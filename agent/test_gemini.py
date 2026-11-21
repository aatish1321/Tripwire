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
    print("offline OK: retry once on 503/timeout, then fallback; other errors are not retried")


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
