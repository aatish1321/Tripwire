"""Manager agent: routes every tool result to the Scanner and Sanitizer, and every proposed action to the Guard and
Judge (in interceptor.check). Routing is rule-based, so the manager itself can't be talked into skipping a check.

Every agent reports a step: {"agent", "status": ok|flag|block|skip, "summary", "evidence": [...], "ms"}."""
import time
from typing import Any

from firewall.sanitizer import sanitize
from firewall.scanner import scan
from firewall.session import Session
from shared.contracts import Provenance, ToolCall, ToolResult

LISTING_TOOLS = {"list_issues", "list_repos"}
ENABLED = {"scanner": True, "sanitizer": True, "guard": True, "judge": True, "llm": True,  # "llm": all LLM calls
           "ask": False}  # B10: off by default, so loops that don't wait for an answer (scoreboard, tests) never get "ask"


def set_enabled(flags: dict[str, bool]) -> None:
    """Switch agents on or off for the next runs, e.g. set_enabled({"scanner": False}). The manager can't be switched off."""
    unknown = set(flags) - set(ENABLED)
    if unknown:
        raise ValueError(f"unknown agents: {sorted(unknown)}")
    ENABLED.update({k: bool(v) for k, v in flags.items()})


def step(agent: str, status: str, summary: str, evidence: list | None = None, ms: float = 0) -> dict:
    return {"agent": agent, "status": status, "summary": summary, "evidence": evidence or [], "ms": round(ms)}


def where(p: Provenance) -> str:
    label = {"issue": "an issue", "repo_file": "a file", "tool_meta": "a listing"}.get(p["source"], p["source"])
    by = f" by {p['author']}" if p["author"] else ""
    return f"{label}{by} in {p['repo']}" if p["repo"] else f"{label}{by}"


def _ms(t: float) -> float:
    return (time.monotonic() - t) * 1000


def inspect_result(session: Session, call: ToolCall, result: ToolResult) -> tuple[Any, list[dict]]:
    """Runs AFTER an allowed tool, BEFORE the main agent sees the output.
    Returns (clean_output to give the model, agent steps for the UI). Findings also taint the session."""
    start = time.monotonic()
    p = result["provenance"]
    trust = "trusted" if p["trusted"] else "UNTRUSTED"
    manager = step("manager", "ok", f"{call['tool']} returned {where(p)} ({trust}) → Scanner, then Sanitizer")
    steps = [manager]

    findings: list[dict] = []
    t = time.monotonic()
    if ENABLED["scanner"]:
        # listings are short titles: the patterns are enough, and the LLM pass both slowed them and gave false alarms
        findings = scan(result["output"], p, use_llm=ENABLED["llm"] and call["tool"] not in LISTING_TOOLS)
        if findings:
            techniques = ", ".join(sorted({f["technique"].replace("_", " ") for f in findings}))
            steps.append(step("scanner", "flag", f"Found {len(findings)} hidden instruction(s) in {where(p)}: {techniques}",
                              findings, _ms(t)))
            session["findings"] += [{**f, "where": where(p)} for f in findings]
            session["tainted"] = True  # a hidden instruction taints the session even in the user's own content
            session["taint_sources"].append({"source": "hidden instruction", "author": p["author"], "repo": p["repo"]})
        else:
            steps.append(step("scanner", "ok", "No injection signs found", ms=_ms(t)))
    else:
        steps.append(step("scanner", "skip", "Scanner switched off"))

    t = time.monotonic()
    if ENABLED["sanitizer"]:
        clean = sanitize(result["output"], findings, p)
        parts = [f"quarantined {len(findings)} flagged part(s)"] if findings else []
        if not p["trusted"]:
            parts.append(f"marked as data from {p['author']}, not instructions")
        steps.append(step("sanitizer", "flag" if findings else "ok",
                          ("Sanitized: " + "; ".join(parts)) if parts else "Nothing to clean; passed through", ms=_ms(t)))
    else:
        clean = result["output"]
        steps.append(step("sanitizer", "skip", "Sanitizer switched off: the agent sees the raw output"))

    manager["ms"] = round(_ms(start))
    return clean, steps
