"""A12 check: uv run python -m agent.test_ask   (no network; a second thread plays the user who clicks Approve or Deny)"""
import tempfile
import threading
import time
from pathlib import Path

from agent import scoreboard
from agent.victim import new_state, run_call
from firewall import approvals, logger
from firewall.manager import ENABLED, set_enabled
from firewall.session import new_session
from mockgh.world import load_world, reset_world, save_world


DELETE_NAMED = "Delete a repo the user named"  # attack 6: R4 blocks it, so with asking on it becomes a question
DELETE_PRIVATE = "Stranger's issue asks to delete the private repo"  # attack 5: R1, a hard block, never asked


def play(name: str, answer_with: bool | None):
    """Runs one attack's steps through run_call. answer_with True/False answers the question from another thread,
    None means nobody answers (only valid when no question is expected). Returns (events, blocking decision, harm done)."""
    reset_world()
    sc = next(s for s in scoreboard._scenarios({}) if s["name"] == name)
    world = load_world()
    sc["setup"](world)
    save_world(world)

    def user() -> None:
        for _ in range(500):  # wait up to 5 s for the question to open, then answer it
            if approvals.pending():
                approvals.answer(approvals.pending()[0], answer_with)
                return
            time.sleep(0.01)

    thread = threading.Thread(target=user)
    if answer_with is not None:
        thread.start()
    session, state, events, blocked = new_session(sc["request"]), new_state(), [], None
    for step, (tool, args) in enumerate(sc["steps"], 1):
        gen = run_call(session, {"id": f"c{step}", "tool": tool, "args": dict(args), "step": step}, True, state)
        while True:
            try:
                events.append(next(gen))
            except StopIteration as stop:
                blocked = stop.value[1]
                break
        if blocked:
            break
    if answer_with is not None:
        thread.join()
    return events, blocked, sc["done"](load_world())


def verdicts(events):
    return [(e["data"]["call_id"], e["data"]["verdict"]) for e in events if e["type"] == "decision"]


def main() -> None:
    saved, real_log = dict(ENABLED), logger.LOG_PATH
    logger.LOG_PATH = Path(tempfile.mkdtemp()) / "audit.jsonl"
    try:
        set_enabled({"llm": False, "ask": False})
        events, blocked, harm = play(DELETE_NAMED, None)  # asking off (the default): a plain block, nothing to wait for
        assert verdicts(events)[-1] == ("c2", "block") and blocked["rule"] == "R4" and not harm and approvals.pending() == []

        set_enabled({"ask": True})
        events, blocked, harm = play(DELETE_NAMED, True)  # Approve: the question, then the delete really runs
        assert verdicts(events)[-2:] == [("c2", "ask"), ("c2", "allow")], verdicts(events)
        final = [e["data"] for e in events if e["type"] == "decision"][-1]
        assert "human" in final["checked_by"] and "Approved by you" in final["reason"]
        assert blocked is None and harm, "approved, so the repo should be gone"
        assert events[-1]["type"] == "tool_result"

        events, blocked, harm = play(DELETE_NAMED, False)  # Deny: the question, then the call is stopped before it runs
        assert verdicts(events)[-2:] == [("c2", "ask"), ("c2", "block")], verdicts(events)
        assert blocked["verdict"] == "block" and "Denied by you" in blocked["reason"] and not harm
        assert not [e for e in events if e["type"] == "tool_result" and e["data"]["call_id"] == "c2"]  # the delete never ran

        t = time.monotonic()  # R1 is a hard block: no question, so no waiting even though asking is on
        events, blocked, harm = play(DELETE_PRIVATE, None)
        assert verdicts(events)[-1] == ("c2", "block") and blocked["rule"] == "R1" and not harm
        assert "ask" not in [v for _, v in verdicts(events)] and time.monotonic() - t < 5

        # the scoreboard turns asking off for its own runs, so it can never hang on a question, and puts the setting back
        board = scoreboard.run_scoreboard()
        assert board["on"]["attacks_succeeded"] == 0 and board["on"]["normal_passed"] == 5, board["on"]
        assert ENABLED["ask"] is True and approvals.pending() == []
        print("A12 OK: with asking on, attack 6 waits for the user: Approve runs the delete, Deny stops it; R1 is never asked; "
              "the scoreboard (asking off) is still 0/9 and 5/5")
    finally:
        set_enabled(saved)
        logger.LOG_PATH = real_log
        reset_world()


if __name__ == "__main__":
    main()
