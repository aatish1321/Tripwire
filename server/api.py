"""C9: thin JSON/SSE wrapper around the existing engine for the React UI. No logic of its own.
Run: uv run uvicorn server.api:app --port 8000"""
import json
import threading
import time
from pathlib import Path

from anyio import CancelScope
from fastapi import FastAPI, HTTPException
from starlette.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from agent.scoreboard import run_scoreboard
from agent.victim import run_agent
from firewall.agent_fakes import fake_run
from firewall.logger import read_log
from firewall.manager import set_enabled
from mockgh.tools import public_view
from mockgh.world import reset_world

PUBLIC_REPO = "alice/public-site"
DIST = Path(__file__).resolve().parent.parent / "web" / "dist"

app = FastAPI(title="TripWire API")
# shortcut: a single-user demo server (one shared world file and one set_enabled), a real product would isolate each run
_run_lock = threading.Lock()
_run_started = 0.0
_run_token: object = None
STALE_RUN_S = 300  # a run holding the lock longer than this was abandoned (10 steps take well under a minute)
_END = object()


def _json(value) -> str:
    return json.dumps(value, default=str)


@app.get("/api/run")
def run(request: str, firewall_on: int = 1, mode: str = "replay",
        scanner: int = 1, sanitizer: int = 1, guard: int = 1, judge: int = 1):
    if mode not in ("replay", "live", "fake"):
        raise HTTPException(400, f"unknown mode: {mode}")
    token = _acquire_run_lock()

    def events():
        try:
            set_enabled({"scanner": bool(scanner), "sanitizer": bool(sanitizer), "guard": bool(guard), "judge": bool(judge)})
            reset_world()
            yield from (fake_run(bool(firewall_on), request) if mode == "fake" else run_agent(request, bool(firewall_on), mode))
        except Exception as e:  # show engine errors in the UI instead of a silently dropped stream
            yield {'type': 'error', 'data': {'message': f'{type(e).__name__}: {e}'}, 'firewall_on': bool(firewall_on)}

    async def stream():
        gen = events()
        try:
            while True:
                ev = await run_in_threadpool(next, gen, _END)  # one engine step at a time, off the event loop
                if ev is _END:
                    break
                yield f"data: {_json(ev)}\n\n"
        finally:
            # A browser that disconnects mid-run cancels the loop above. Close the engine's generator so its own clean-up
            # runs (e.g. switching real GitHub reads off), then free the lock. Before this, the lock stayed taken forever
            # and every later run got 409.
            with CancelScope(shield=True):
                await run_in_threadpool(gen.close)
            _release_run_lock(token)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def _acquire_run_lock() -> object:
    """Returns this run's token. Only the run holding the current token can release the lock."""
    global _run_started, _run_token
    if not _run_lock.acquire(blocking=False):
        if time.monotonic() - _run_started < STALE_RUN_S:
            raise HTTPException(409, "a run is already in progress: wait for it to finish, or reload in a minute")
        # safety net: no real run takes this long, so the previous one was abandoned without clean-up; it keeps the
        # lock (now ours), and its late release is ignored because its token is no longer current
    _run_started, _run_token = time.monotonic(), object()
    return _run_token


def _release_run_lock(token: object) -> None:
    global _run_token
    if token is _run_token:
        _run_token = None
        _run_lock.release()


@app.post("/api/reset")
def reset():
    if _run_lock.locked():
        raise HTTPException(409, "a run is in progress")
    reset_world()
    return {"ok": True}


@app.get("/api/public-view")
def get_public_view():
    return json.loads(_json(public_view(PUBLIC_REPO)))


@app.get("/api/audit")
def audit():
    return json.loads(_json(read_log()))


@app.get("/api/scoreboard")
def scoreboard(scanner: int = 1, sanitizer: int = 1, guard: int = 1, judge: int = 1):
    if not _run_lock.acquire(blocking=False):  # it rewrites the shared world file
        raise HTTPException(409, "a run is in progress")
    try:
        layers = {"scanner": bool(scanner), "sanitizer": bool(sanitizer), "guard": bool(guard), "judge": bool(judge)}
        return json.loads(_json(run_scoreboard(layers=layers)))
    finally:
        _run_lock.release()


if DIST.is_dir():  # after `npm run build` in web/, the same process serves the React app (mounted last, after /api)
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
