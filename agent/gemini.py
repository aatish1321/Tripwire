"""The one place that calls Gemini. On a 503/overloaded error or a timeout it retries once,
then switches to the fallback model."""
import os
import random
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from httpx2 import TransportError  # timeouts and connection errors; httpx2 is google-genai's HTTP library

GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_FALLBACK_MODEL = "gemini-3.8-flash"
RETRIES = 1
TIMEOUT_MS = 15_000

load_dotenv()
_client = None


def _retryable(e: Exception) -> bool:
    if isinstance(e, errors.APIError):
        return e.code in (503, 504) or "overloaded" in str(e).lower()  # 504 = Gemini's own server-side timeout
    return isinstance(e, TransportError)


def generate(contents, tools: list | None = None, system_instruction: str | None = None):
    """Call Gemini with function calling (manual: we run the tools). Returns the raw response;
    use response.function_calls for the proposed tool calls."""
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
    raise last  # both models failed
