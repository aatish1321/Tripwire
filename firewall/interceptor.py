"""B3: check(session, call) runs BEFORE the tool. The first rule that objects blocks the call."""
from firewall.logger import log_decision
from firewall.rules import RULES
from firewall.session import Session
from shared.contracts import Decision, ToolCall

ALLOW_REASON = "This matches what you asked for."


def check(session: Session, call: ToolCall) -> Decision:
    decision: Decision = {"call_id": call["id"], "verdict": "allow", "rule": None, "reason": ALLOW_REASON,
                          "checked_by": ["rules"]}
    for rule in RULES:
        hit = rule(session, call)
        if hit:
            decision.update(verdict="block", rule=hit[0], reason=hit[1])
            break
    log_decision(session, call, decision)
    return decision
