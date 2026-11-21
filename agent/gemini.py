"""The one place that calls an LLM. Gemini first: on a 503/overloaded error or a timeout it retries once, then
switches to the fallback Gemini model. If Gemini still fails (or the key/quota is bad) and GROQ_API_KEY is set,
the same request goes to Groq. Groq's answer is converted to a Gemini-shaped response, so callers don't care."""
import json
import os
import random
import time

import httpx2  # google-genai's own HTTP library, so Groq needs no new dependency
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from httpx2 import TransportError  # timeouts and connection errors

GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_FALLBACK_MODEL = "gemini-3.8-flash"
# checked against GET /openai/v1/models; all three did tool calls. On a 429 the next one is tried (separate limits per model).
GROQ_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
RETRIES = 1
TIMEOUT_MS = 15_000

load_dotenv()
_client = None


def _retryable(e: Exception) -> bool:
    if isinstance(e, errors.APIError):
        return e.code in (503, 504) or "overloaded" in str(e).lower()  # 504 = Gemini's own server-side timeout
    return isinstance(e, TransportError)


def _generate_gemini(contents, tools, system_instruction):
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"],
                               http_options=types.HttpOptions(timeout=TIMEOUT_MS))
    config = types.GenerateContentConfig(
        tools=tools,
        system_instruction=system_instruction,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    for model in (GEMINI_MODEL, GEMINI_FALLBACK_MODEL):
        for attempt in range(RETRIES + 1):
            try:
                return _client.models.generate_content(model=model, contents=contents, config=config)
            except (errors.APIError, TransportError) as e:
                if not _retryable(e):
                    raise
                last = e
                if attempt < RETRIES:
                    time.sleep(random.uniform(1, 2))
    raise last  # both Gemini models failed


# ---- Groq (OpenAI-compatible chat API) ----

def _to_openai_messages(contents, system_instruction) -> list[dict]:
    if isinstance(contents, str):  # Gemini accepts a bare string as a single user message
        contents = [types.Content(role="user", parts=[types.Part(text=contents)])]
    msgs = [{"role": "system", "content": system_instruction}] if system_instruction else []
    n, pending = 0, []  # pending: ids of tool calls still waiting for their reply, in order
    for c in contents:
        text = "".join(p.text for p in c.parts if p.text)
        if c.role == "model":
            m = {"role": "assistant", "content": text or None}
            calls = [p.function_call for p in c.parts if p.function_call]
            if calls:
                m["tool_calls"] = []
                for fc in calls:
                    n += 1
                    pending.append(f"call_{n}")
                    m["tool_calls"].append({"id": pending[-1], "type": "function",
                                            "function": {"name": fc.name, "arguments": json.dumps(dict(fc.args or {}))}})
            msgs.append(m)
        else:
            for p in c.parts:  # replies come back in the same order as the calls (victim.py guarantees it)
                if p.function_response:
                    msgs.append({"role": "tool", "tool_call_id": pending.pop(0),
                                 "content": json.dumps(p.function_response.response, default=str)})
            if text:
                msgs.append({"role": "user", "content": text})
    return msgs


def _to_openai_tools(tools) -> list[dict]:
    return [{"type": "function", "function": {"name": d.name, "description": d.description,
                                              "parameters": d.parameters_json_schema}}
            for t in tools or [] for d in t.function_declarations]


def _groq_post(payload: dict) -> dict:
    r = httpx2.post(GROQ_URL, json=payload, headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
                    timeout=TIMEOUT_MS / 1000)
    r.raise_for_status()
    return r.json()


def _generate_groq(contents, tools, system_instruction):
    payload = {"messages": _to_openai_messages(contents, system_instruction)}
    if tools:
        payload["tools"] = _to_openai_tools(tools)
    for i, model in enumerate(GROQ_MODELS):
        try:
            msg = _groq_post({**payload, "model": model})["choices"][0]["message"]
            break
        except httpx2.HTTPStatusError as e:
            if e.response.status_code != 429 or i == len(GROQ_MODELS) - 1:
                raise
            time.sleep(2)  # rate limited: give it a moment, then the next model (each has its own limit)
    parts = [types.Part(text=msg["content"])] if msg.get("content") else []
    for tc in msg.get("tool_calls") or []:
        args = json.loads(tc["function"]["arguments"] or "{}")
        parts.append(types.Part(function_call=types.FunctionCall(name=tc["function"]["name"], args=args)))
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role="model", parts=parts))],
                                         model_version=f"groq:{model}")


def generate(contents, tools: list | None = None, system_instruction: str | None = None):
    """Call the LLM with function calling (manual: we run the tools). Returns a Gemini-shaped response;
    use response.function_calls for the proposed tool calls and response.model_version for who answered."""
    try:
        return _generate_gemini(contents, tools, system_instruction)
    except (errors.APIError, TransportError):
        if not os.environ.get("GROQ_API_KEY"):
            raise
        return _generate_groq(contents, tools, system_instruction)
