"""B10: "ask the human". check() opens a question for a grey-zone call; the agent loop waits in wait_for_human();
the UI answers through answer(). No answer in time counts as Deny."""
import threading

from firewall.logger import log_decision
from firewall.manager import step
from firewall.session import Session
from shared.contracts import Decision, ToolCall

ASK_TIMEOUT_S = 60
# shortcut: one shared table keyed by call_id ("c1", "c2", …), fine for one run at a time; key by session too if runs overlap
_open: dict[str, threading.Event] = {}
_answers: dict[str, bool] = {}
_lock = threading.Lock()


def open_question(call_id: str) -> None:
    with _lock:
        _open[call_id] = threading.Event()
        _answers.pop(call_id, None)


def pending() -> list[str]:
    with _lock:
        return [c for c, ev in _open.items() if not ev.is_set()]


def answer(call_id: str, approved: bool) -> bool:
    """Called by the UI. Returns False if nothing is waiting for that call_id (already answered or timed out)."""
    with _lock:
        ev = _open.get(call_id)
        if ev is None or ev.is_set():
            return False
        _answers[call_id] = bool(approved)
        ev.set()
        return True


def wait_for_human(session: Session, call: ToolCall, decision: Decision, timeout: float = ASK_TIMEOUT_S) -> Decision:
    """Called by the agent loop after check() returned "ask". Blocks until answered or timed out,
    then returns (and logs) the final allow/block decision."""
    with _lock:
        ev = _open.get(call["id"])
    got = ev.wait(timeout) if ev else False
    with _lock:
        approved = got and _answers.pop(call["id"], False)
        _open.pop(call["id"], None)  # a late click after the timeout finds nothing and changes nothing
    if approved:
        verdict, status, reason = "allow", "ok", f"Approved by you. (The firewall had asked because: {decision['reason']})"
    elif got:
        verdict, status, reason = "block", "block", f"Denied by you. {decision['reason']}"
    else:
        verdict, status, reason = "block", "block", f"No answer within {timeout:g} seconds, so it was blocked. {decision['reason']}"
    final: Decision = {**decision, "verdict": verdict, "reason": reason, "checked_by": decision["checked_by"] + ["human"]}
    final["agents"] = decision.get("agents", []) + [step("judge", status, reason)]
    log_decision(session, call, final)
    return final
