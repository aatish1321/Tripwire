"""C2: tool-call timeline. One card per tool call: call -> decision badge -> short result."""
import html

import streamlit as st

from ui.agents_view import COLOR, ICON, ORDER, RANK
from ui.github_view import highlight

CSS = """
<style>
.tl-tool { font-size: 1.35rem; font-weight: 700; }
.tl-args { font-family: monospace; font-size: 1.05rem; opacity: 0.85; word-break: break-word; }
.tl-badge { display: inline-block; padding: 0.25rem 0.8rem; border-radius: 999px;
            font-size: 1.1rem; font-weight: 700; margin: 0.4rem 0; }
.tl-allow { background: rgba(33, 195, 84, 0.18); color: #21c354; border: 1px solid #21c354; }
.tl-none  { background: rgba(150, 150, 150, 0.15); color: #9a9a9a; border: 1px solid #9a9a9a; }
.tl-block-box { background: rgba(255, 43, 43, 0.12); border: 2px solid #ff4b4b; border-radius: 0.6rem;
                padding: 0.8rem 1rem; margin: 0.4rem 0; }
.tl-block-title { color: #ff4b4b; font-size: 1.2rem; font-weight: 800; letter-spacing: 0.03em; }
.tl-reason { font-size: 1.6rem; font-weight: 600; line-height: 1.35; margin-top: 0.3rem; }
.tl-result { font-family: monospace; font-size: 0.95rem; opacity: 0.7; white-space: pre-wrap;
             word-break: break-word; }
.tl-user { font-size: 1.25rem; }
.tl-chain { margin: 0.3rem 0; font-size: 1.05rem; }
.tl-chip { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-weight: 700; margin: 0.1rem 0; }
.tl-quote { font-size: 1.25rem; font-style: italic; margin-top: 0.5rem; border-left: 4px solid #ff4b4b; padding-left: 0.7rem; }
.tl-cmp { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; margin-top: 0.4rem; }
.tl-cmp div { font-family: monospace; font-size: 0.95rem; white-space: pre-wrap; word-break: break-word;
              border: 1px solid #8884; border-radius: 0.4rem; padding: 0.5rem; }
details summary { cursor: pointer; font-weight: 700; font-size: 1.05rem; }
.tl-leak { background: #ff2b2b; color: white; border-radius: 0.6rem; padding: 0.8rem 1rem;
           font-size: 1.4rem; font-weight: 800; margin: 0.4rem 0; }
</style>
"""


def _short(value, limit: int) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _args(args: dict) -> str:
    return ", ".join(f"{k}={_short(repr(v), 60)}" for k, v in args.items())


def _text(output) -> str:
    """Readable text for a tool output, without JSON escaping, so evidence strings still match."""
    if isinstance(output, dict):
        return "\n".join(f"{k}: {v}" for k, v in output.items())
    if isinstance(output, list):
        return "\n".join(", ".join(f"{k}: {v}" for k, v in x.items()) if isinstance(x, dict) else str(x) for x in output)
    return str(output)


def _chain(steps: list[dict]) -> str:
    """Manager → Scanner → Sanitizer → Guard → Judge, each with its worst status for this call."""
    status = {}
    for s in steps:
        status[s["agent"]] = max(status.get(s["agent"]), s["status"], key=RANK.get)
    chips = []
    for a in ORDER:
        st_, c = status.get(a), COLOR[status.get(a)]
        chips.append(f'<span class="tl-chip" style="border:2px solid {c};background:{c}22">'
                     f'{ICON[a]} {a.capitalize()} {(st_ or "–").upper()}</span>')
    return '<div class="tl-chain">' + " → ".join(chips) + "</div>"


def _group(events: list[dict]) -> list[tuple[str, dict]]:
    """Turn the flat event stream into timeline items; decisions/results attach to their call."""
    items: list[tuple[str, dict]] = []
    calls: dict[str, dict] = {}
    for ev in events:
        t, d = ev["type"], ev["data"]
        if t == "tool_call":
            card = {"call": d, "decision": None, "result": None, "firewall_on": ev["firewall_on"]}
            calls[d["id"]] = card
            items.append(("call", card))
        elif t == "decision" and d["call_id"] in calls:
            calls[d["call_id"]]["decision"] = d
        elif t == "tool_result" and d["call_id"] in calls:
            calls[d["call_id"]]["result"] = d
        else:
            items.append((t, d))
    return items


def _call_card(card: dict) -> None:
    call, decision, result = card["call"], card["decision"], card["result"]
    with st.container(border=True):
        st.markdown(
            f'<div class="tl-tool">Step {call["step"]} · {html.escape(call["tool"])}</div>'
            f'<div class="tl-args">{html.escape(_args(call["args"]))}</div>',
            unsafe_allow_html=True,
        )
        steps = (decision or {}).get("agents", []) + (result or {}).get("agents", [])
        if steps:
            st.markdown(_chain(steps), unsafe_allow_html=True)
        if decision and decision["verdict"] == "block":
            rule = f' · {html.escape(decision["rule"])}' if decision.get("rule") else ""
            quotes = list(dict.fromkeys(e["text"] for s in decision.get("agents", []) if s["status"] == "block"
                                        for e in s["evidence"]))
            quote = "".join(f'<div class="tl-quote">Evidence: “{html.escape(q)}”</div>' for q in quotes)
            st.markdown(
                f'<div class="tl-block-box"><div class="tl-block-title">⛔ BLOCKED{rule}</div>'
                f'<div class="tl-reason">{html.escape(decision["reason"])}</div>{quote}</div>',
                unsafe_allow_html=True,
            )
        elif decision:
            st.markdown('<span class="tl-badge tl-allow">✅ Allowed</span>', unsafe_allow_html=True)
        elif not card["firewall_on"]:
            st.markdown('<span class="tl-badge tl-none">⚪ No firewall: ran unchecked</span>',
                        unsafe_allow_html=True)
        if result:
            st.markdown(f'<div class="tl-result">→ {html.escape(_short(result["output"], 160))}</div>',
                        unsafe_allow_html=True)
            found = [e["text"] for s in result.get("agents", []) for e in s["evidence"]]
            if found or result.get("clean_output", result["output"]) != result["output"]:  # only when there's a difference
                title = f"⚠️ {len(set(found))} hidden instruction(s) found · raw vs what the AI saw"
                st.markdown(
                    f'<details><summary>{title}</summary><div class="tl-cmp">'
                    f'<div><b>Raw</b><br>{highlight(_text(result["output"]), found).replace(chr(10), "<br>")}</div>'
                    f'<div><b>What the AI saw</b><br>{html.escape(_text(result["clean_output"])).replace(chr(10), "<br>")}'
                    f'</div></div></details>', unsafe_allow_html=True)


def render_timeline(events: list[dict]) -> None:
    """Draw the whole timeline. Call it again after each new event to stream."""
    st.markdown(CSS, unsafe_allow_html=True)
    if not events:
        st.caption("Press Run to start the agent.")
        return
    for kind, d in _group(events):
        if kind == "call":
            _call_card(d)
        elif kind == "user":
            label = " <i>(scripted replay)</i>" if d.get("scripted") else ""
            st.markdown(f'<div class="tl-user">👤 <b>User:</b> {html.escape(d["text"])}{label}</div>',
                        unsafe_allow_html=True)
        elif kind == "agent_text":
            st.markdown(f"🤖 {d.get('text', '')}")
        elif kind == "leak":
            what = ("Agent read private repo {} after a stranger's instructions" if d.get("kind") == "private_read"
                    else "Private data leaked into public repo {}")
            st.markdown(f'<div class="tl-leak">🚨 {what.format(html.escape(d["repo"]))}</div>',
                        unsafe_allow_html=True)
        elif kind == "final":
            st.info(f"🤖 {d['text']}")
        elif kind == "error":
            st.warning(f"Error: {d.get('message', d)}")
