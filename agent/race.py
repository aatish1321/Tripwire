"""A13: the race. The same scripted attack runs with the firewall OFF and ON at the same time, each in its own isolated
world, so a screen can show both side by side and the viewer watches one leak while the other is stopped.

    for item in run_race(request):
        item["side"]                           # "off" or "on"
        item["event"], item["public"], item["attacker"]   # a RunEvent, then what a stranger sees in the repo right after it
        item.get("done")                       # last item of a side: item["outcome"] is leaked|blocked|clean|error, and
                                               # item["headline"] is the firewall's one-sentence reason when blocked

Replay only: two live model runs at once would double the API calls. Issue #1 is the hidden-text version, so what a
human reads is friendly (see agent/xray.py). One side's world never touches the other's, or the shared world.json."""
import queue
import threading
import time
from typing import Iterator

from agent.victim import run_agent
from mockgh.tools import attacker_view, public_view
from mockgh.variants import hide_issue_1
from mockgh.world import isolated_world, load_world, save_world

PUBLIC_REPO = "alice/public-site"
SIDES = {"off": False, "on": True}


def _outcome(events: list[dict]) -> tuple[str, str]:
    block = next((e["data"] for e in events if e["type"] == "decision" and e["data"]["verdict"] == "block"), None)
    if block:
        return "blocked", block["reason"]
    if any(e["type"] == "leak" and e["data"].get("private_text") for e in events):
        return "leaked", "Private data reached the public repo."
    if any(e["type"] == "error" for e in events):
        return "error", next(e["data"]["message"] for e in events if e["type"] == "error")
    return "clean", ""


def _snapshot(side: str, event: dict) -> dict:
    return {"side": side, "event": event, "public": public_view(PUBLIC_REPO), "attacker": attacker_view(PUBLIC_REPO)}


def _worker(side: str, firewall_on: bool, request: str, hidden: bool, beat: float, out: queue.Queue,
            stop: threading.Event) -> None:
    events: list[dict] = []
    try:
        with isolated_world():  # everything below, including the tools and the firewall's rules, uses this private copy
            if hidden:
                world = load_world()
                hide_issue_1(world)
                save_world(world)
            for ev in run_agent(request, firewall_on, "replay"):
                if stop.is_set():
                    return
                events.append(ev)
                out.put(_snapshot(side, ev))
                if beat and ev["type"] == "tool_call":  # one beat per step: both sides reach step N together
                    time.sleep(beat)
    except Exception as e:  # show engine errors in the race instead of leaving a side silent
        ev = {"type": "error", "data": {"message": f"{type(e).__name__}: {e}"}, "firewall_on": firewall_on}
        events.append(ev)
        out.put({"side": side, "event": ev, "public": None, "attacker": None})
    finally:
        outcome, headline = _outcome(events)
        out.put({"side": side, "done": True, "outcome": outcome, "headline": headline})


def run_race(request: str, mode: str = "replay", hidden: bool = True, beat: float = 0.0) -> Iterator[dict]:
    """beat: seconds to wait after each tool call, so a viewer can follow (0 = as fast as possible)."""
    if mode != "replay":
        raise ValueError("a race only supports mode='replay' (two live runs would double the API calls)")
    out: queue.Queue = queue.Queue()
    stop = threading.Event()
    for side, firewall_on in SIDES.items():
        threading.Thread(target=_worker, args=(side, firewall_on, request, hidden, beat, out, stop), daemon=True).start()
    try:
        finished = 0
        while finished < len(SIDES):
            item = out.get()
            finished += bool(item.get("done"))
            yield item
    finally:
        stop.set()  # the consumer left early (for example the browser closed): let the workers stop
