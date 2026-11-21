"""B3/B4: check(session, call) runs BEFORE the tool. Rules decide; the policy agent explains,
and may block an allowed write that came from untrusted content."""
from firewall.logger import log_decision
from firewall.policy_agent import ask_policy
from firewall.rules import RULES, is_write
from firewall.session import Session
from shared.contracts import Decision, ToolCall

ALLOW_REASON = "This matches what you asked for."


def check(session: Session, call: ToolCall) -> Decision:
    decision: Decision = {"call_id": call["id"], "verdict": "allow", "rule": None, "reason": ALLOW_REASON,
                          "checked_by": ["rules"]}
    hit = next((h for h in (rule(session, call) for rule in RULES) if h), None)
    if hit:
        decision.update(verdict="block", rule=hit[0], reason=hit[1])
    if hit or is_write(call):
        policy = ask_policy(session, call)  # None on error/timeout: the rule's verdict and template reason stand
        if policy:
            decision["checked_by"].append("policy_agent")
            if hit:
                decision["reason"] = policy["reason"]
            elif not policy["matches_request"] and policy["instruction_source"] == "untrusted_content":
                decision.update(verdict="block", rule="POLICY", reason=policy["reason"])
    log_decision(session, call, decision)
    return decision
