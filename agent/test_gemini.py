"""A3 check: uv run python -m agent.test_gemini
Part 1 is offline (retry and fallback logic with a stub client). Part 2 makes one real Gemini call."""
import httpx2
from google.genai import errors

from agent import gemini
from mockgh.tools import TOOL_SPECS


class _Stub:
    """Fake client: models.generate_content raises 503 for the listed models, otherwise returns the model name."""
    def __init__(self, overloaded: set[str], code: int = 503, timeout: bool = False):
        self.calls, self.overloaded, self.code, self.timeout = [], overloaded, code, timeout
        self.models = self

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        if model in self.overloaded and self.timeout:
            raise httpx2.ReadTimeout("timed out")
        if model in self.overloaded:
            msg = "The model is overloaded" if self.code == 503 else "Invalid argument"
            raise errors.ServerError(self.code, {"error": {"message": msg}})
        return model


def offline() -> None:
    import os
    saved = os.environ.pop("GROQ_API_KEY", None)  # a real key in .env would turn these stub tests into real Groq calls
    try:
        _offline()
    finally:
        if saved is not None:
            os.environ["GROQ_API_KEY"] = saved


def _offline() -> None:
    gemini.time.sleep = lambda s: None
    P, F = gemini.GEMINI_MODEL, gemini.GEMINI_FALLBACK_MODEL

    gemini._client = s = _Stub(set())
    assert gemini.generate("hi") == P and s.calls == [P]  # healthy: one call

    gemini._client = s = _Stub({P})
    assert gemini.generate("hi") == F and s.calls == [P, P, F]  # 1 try + 1 retry, then fallback

    gemini._client = s = _Stub({P, F})
    try:
        gemini.generate("hi")
        raise AssertionError("expected the error to surface")
    except errors.ServerError:
        assert s.calls == [P, P, F, F]

    gemini._client = s = _Stub({P}, timeout=True)  # a timeout is retried once, then fallback
    assert gemini.generate("hi") == F and s.calls == [P, P, F]

    gemini._client = s = _Stub({P}, code=504)  # Gemini's server-side DEADLINE_EXCEEDED counts as a timeout
    assert gemini.generate("hi") == F and s.calls == [P, P, F]

    gemini._client = s = _Stub({P}, code=400)  # not an overload error: no retry, no fallback
    try:
        gemini.generate("hi")
        raise AssertionError("expected the error to surface")
    except errors.ServerError:
        assert s.calls == [P]
    gemini._client = None
    groq_fallback()
    print("offline OK: retry once on 503/timeout, then fallback; other errors are not retried; Groq fallback")


def groq_fallback() -> None:
    """Gemini fails -> the same request goes to Groq, converted both ways. No network: _groq_post is a stub."""
    import os
    from google.genai import types
    sent = []
    def fake_post(payload):
        sent.append(payload)
        return {"choices": [{"message": {"content": None, "tool_calls": [
            {"id": "x", "type": "function", "function": {"name": "get_issue", "arguments": '{"repo": "a/b", "number": 1}'}}]}}]}
    gemini._groq_post = fake_post
    contents = [
        types.Content(role="user", parts=[types.Part(text="do it")]),
        types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(name="list_repos", args={"owner": "alice"})),
                                           types.Part(function_call=types.FunctionCall(name="get_file", args={"repo": "a/b", "path": "x"}))]),
        types.Content(role="user", parts=[
            types.Part.from_function_response(name="list_repos", response={"result": ["a/b"]}),
            types.Part.from_function_response(name="get_file", response={"error": "BLOCKED by firewall: no"})]),
    ]
    old_key, os.environ["GROQ_API_KEY"] = os.environ.get("GROQ_API_KEY"), "test"
    try:
        gemini._client = _Stub({gemini.GEMINI_MODEL, gemini.GEMINI_FALLBACK_MODEL})
        r = gemini.generate(contents, tools=TOOL_SPECS, system_instruction="be naive")
        assert r.function_calls[0].name == "get_issue" and dict(r.function_calls[0].args) == {"repo": "a/b", "number": 1}
        assert r.model_version == f"groq:{gemini.GROQ_MODELS[0]}"
        roles = [m["role"] for m in sent[0]["messages"]]
        assert roles == ["system", "user", "assistant", "tool", "tool"], roles
        m = sent[0]["messages"]
        assert [t["id"] for t in m[2]["tool_calls"]] == [m[3]["tool_call_id"], m[4]["tool_call_id"]]  # replies matched to calls
        assert "BLOCKED by firewall" in m[4]["content"]
        assert [t["function"]["name"] for t in sent[0]["tools"]] == ["list_repos", "list_issues", "get_issue", "get_file", "create_pull_request"]

        gemini._client = _Stub({gemini.GEMINI_MODEL, gemini.GEMINI_FALLBACK_MODEL}, code=429)  # quota / bad key also fall back
        assert gemini.generate("hi").function_calls[0].name == "get_issue"

        # Groq 429 on a model -> wait, try the next one; all rate limited -> the 429 surfaces
        def limited(*blocked):
            def post(payload):
                if payload["model"] in blocked:
                    raise httpx2.HTTPStatusError("429", request=httpx2.Request("POST", gemini.GROQ_URL), response=httpx2.Response(429))
                return fake_post(payload)
            return post
        M = gemini.GROQ_MODELS
        gemini._groq_post = limited(M[0])
        assert gemini.generate("hi").model_version == f"groq:{M[1]}"
        gemini._groq_post = limited(M[0], M[1])
        assert gemini.generate("hi").model_version == f"groq:{M[2]}"
        gemini._groq_post = limited(*M)
        try:
            gemini.generate("hi")
            raise AssertionError("expected the 429 to surface")
        except httpx2.HTTPStatusError:
            pass
        gemini._groq_post = fake_post

        del os.environ["GROQ_API_KEY"]  # no Groq key: the Gemini error surfaces unchanged
        try:
            gemini.generate("hi")
            raise AssertionError("expected the Gemini error")
        except errors.ServerError:
            pass
    finally:
        gemini._client = None
        os.environ.pop("GROQ_API_KEY", None)
        if old_key is not None:
            os.environ["GROQ_API_KEY"] = old_key


def live() -> None:
    get_issue = [t for t in TOOL_SPECS[0].function_declarations if t.name == "get_issue"]
    from google.genai import types
    one_tool = [types.Tool(function_declarations=get_issue)]
    r = gemini.generate("Read issue number 1 in the repo alice/public-site.", tools=one_tool)
    calls = r.function_calls
    assert calls and calls[0].name == "get_issue", f"no function call, got: {r.text!r}"
    print("live OK:", calls[0].name, dict(calls[0].args), "| answered by:", r.model_version)


if __name__ == "__main__":
    offline()
    live()
