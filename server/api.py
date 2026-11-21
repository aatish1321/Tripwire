"""C9: thin JSON/SSE wrapper around the existing engine for the React UI. No logic of its own.
Run: uv run uvicorn server.api:app --port 8000"""
import json
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
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


def _json(value) -> str:
    return json.dumps(value, default=str)


@app.get("/api/run")
def run(request: str, firewall_on: int = 1, mode: str = "replay",
        scanner: int = 1, sanitizer: int = 1, guard: int = 1, judge: int = 1):
    if mode not in ("replay", "live", "fake"):
        raise HTTPException(400, f"unknown mode: {mode}")
    if not _run_lock.acquire(blocking=False):
        raise HTTPException(409, "a run is already in progress")

    def stream():
        try:
            set_enabled({"scanner": bool(scanner), "sanitizer": bool(sanitizer), "guard": bool(guard), "judge": bool(judge)})
            reset_world()
            events = fake_run(bool(firewall_on), request) if mode == "fake" else run_agent(request, bool(firewall_on), mode)
            for ev in events:
                yield f"data: {_json(ev)}\n\n"
        except Exception as e:  # show engine errors in the UI instead of a silently dropped stream
            yield f"data: {_json({'type': 'error', 'data': {'message': f'{type(e).__name__}: {e}'}, 'firewall_on': bool(firewall_on)})}\n\n"
        finally:
            _run_lock.release()  # also runs when the browser disconnects mid-stream

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


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
