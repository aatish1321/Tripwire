"""check(session, call) runs BEFORE the tool: the Manager sends the call to the Guard (rules R1-R4, plus the LLM
intent check for writes) and then the Judge (plain-language reason with the scanner's evidence, and the audit log).
Rules decide; the LLM can add a block but never remove one."""
import time

from firewall.logger import log_decision
from firewall.manager import ENABLED, step, _ms
from firewall.policy_agent import ask_policy
from firewall.rules import RULES, is_write
from firewall.session import Session
from shared.contracts import Decision, ToolCall

ALLOW_REASON = "This matches what you asked for."


def _evidence(session: Session, call: ToolCall) -> list[dict]:
    """Findings that name the repo this call touches come first: they're the likely source of the instruction."""
    repo = str(call["args"].get("repo") or "").lower()
    names = lambda f: bool(repo) and repo in (f["text"] + f.get("decoded", "")).lower()
    return sorted(session["findings"], key=lambda f: not names(f))[:5]


def _judge_template(reason: str, evidence: list[dict]) -> str:
    if not evidence:
        return reason
    f = evidence[0]
    quote = f.get("decoded") or f["text"]
    return f"{reason} Evidence: {f['technique'].replace('_', ' ')} in {f['where']}: \"{quote[:100]}\""


def check(session: Session, call: ToolCall) -> Decision:
    start = time.monotonic()
    repo = call["args"].get("repo")
    kind = "write" if is_write(call) else "read"
    manager = step("manager", "ok", f"Proposed {kind}: {call['tool']}{f' on {repo}' if repo else ''} → Guard, then Judge")
    decision: Decision = {"call_id": call["id"], "verdict": "allow", "rule": None, "reason": ALLOW_REASON,
                          "checked_by": ["rules"]}
    steps = [manager]

    if not ENABLED["guard"]:
        decision.update(reason="Guard switched off: nothing was checked.", checked_by=[])
        steps += [step("guard", "skip", "Guard switched off"), step("judge", "skip", "Nothing to judge")]
        decision["agents"] = steps  # extra key for the UI: the agent steps behind this decision
        log_decision(session, call, decision)
        return decision

    t = time.monotonic()
    hit = next((h for h in (rule(session, call) for rule in RULES) if h), None)
    if hit:
        decision.update(verdict="block", rule=hit[0], reason=hit[1])
    policy = None
    # one LLM call serves both: the Guard's intent check on writes, and the Judge's wording on blocks
    if ENABLED["llm"] and ((hit and ENABLED["judge"]) or (not hit and is_write(call))):
        policy = ask_policy(session, call)  # None on error/timeout: the rule's verdict and template reason stand
        if policy:
            decision["checked_by"].append("policy_agent")
            if not hit and not policy["matches_request"] and policy["instruction_source"] == "untrusted_content":
                decision.update(verdict="block", rule="POLICY", reason=policy["reason"])
    if hit:
        guard_summary = f"Rule {hit[0]} blocks this call"
    elif decision["rule"] == "POLICY":
        guard_summary = "Rules allow it, but the policy agent traced it to untrusted content: blocked"
    else:
        guard_summary = "All rules pass" + (" and the policy agent agrees" if policy else "")
    guard_status = "block" if decision["verdict"] == "block" else "ok"
    steps.append(step("guard", guard_status, guard_summary, ms=_ms(t)))

    t = time.monotonic()
    if decision["verdict"] == "block" and not ENABLED["judge"]:
        steps.append(step("judge", "skip", "Judge switched off: the rule's own sentence is shown"))
    elif decision["verdict"] == "block":
        evidence = _evidence(session, call)
        if policy and decision["rule"] != "POLICY":
            decision["reason"] = policy["reason"]  # the LLM's wording, which can cite the scanner's evidence
        else:
            decision["reason"] = _judge_template(decision["reason"], evidence)
        steps.append(step("judge", "block", decision["reason"], evidence, _ms(t)))
    else:
        steps.append(step("judge", "ok", decision["reason"], ms=_ms(t)))

    manager["ms"] = round(_ms(start))
    decision["agents"] = steps  # extra key for the UI: the agent steps behind this decision
    log_decision(session, call, decision)
    return decision
