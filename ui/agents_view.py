"""Agent control room: Manager in the middle, Scanner / Sanitizer / Guard / Judge around it."""
import html

import streamlit as st

ORDER = ["manager", "scanner", "sanitizer", "guard", "judge"]
ICON = {"manager": "🧭", "scanner": "🔎", "sanitizer": "🧼", "guard": "🛡️", "judge": "⚖️"}
COLOR = {"ok": "#21c354", "flag": "#ffb020", "block": "#ff4b4b", "skip": "#8a8a8a", None: "#555"}
RANK = {None: 0, "skip": 1, "ok": 2, "flag": 3, "block": 4}
GRID = [["scanner", None, "sanitizer"], [None, "manager", None], ["guard", None, "judge"]]


def steps_by_agent(events: list[dict]) -> dict[str, list[dict]]:
    """agent -> its steps in this run, each tagged with the tool call step number."""
    out = {a: [] for a in ORDER}
    calls = {}
    for ev in events:
        d = ev["data"]
        if ev["type"] == "tool_call":
            calls[d["id"]] = d
        for s in d.get("agents", []) if isinstance(d, dict) else []:
            call = calls.get(d.get("call_id"), {})
            out.setdefault(s["agent"], []).append({**s, "call": f"Step {call.get('step', '?')} · {call.get('tool', '')}"})
    return out


def worst(steps: list[dict]):
    return max((s["status"] for s in steps), key=RANK.get, default=None)


def _label(agent: str, status) -> str:
    return f"{ICON[agent]} {agent.capitalize()} · {(status or 'idle').upper()}"


def render_room(events: list[dict], active: str | None = None, interactive: bool = False) -> None:
    """active: the agent whose step just streamed in (glows). interactive: clickable cards (only once per rerun)."""
    by = steps_by_agent(events)
    status = {a: worst(by[a]) for a in ORDER}
    css = "".join(
        f".st-key-ag_{a} button {{border: 3px solid {COLOR[status[a]]}; background: {COLOR[status[a]]}22;"
        f" min-height: 3.4rem;}} .st-key-ag_{a} button p {{font-size: 1.15rem; font-weight: 700;}}" for a in ORDER)
    st.html(f"""<style>{css}
      .ag-card {{border-radius: 0.6rem; padding: 0.9rem 0.4rem; text-align: center; font-weight: 700;
                 font-size: 1.15rem; min-height: 3.4rem;}}
    </style>""")
    for row in GRID:
        for col, agent in zip(st.columns(3), row):
            if not agent:
                continue
            if interactive:
                if col.container(key=f"ag_{agent}").button(_label(agent, status[agent]), width="stretch"):
                    st.session_state.agent_sel = agent
            else:
                c = COLOR[status[agent]]
                glow = f"box-shadow:0 0 22px 6px {c};" if agent == active else ""
                col.html(f'<div class="ag-card" style="border:3px solid {c};background:{c}22;{glow}">'
                         f'{html.escape(_label(agent, status[agent]))}</div>')
    if interactive:
        _details(by)


def _details(by: dict[str, list[dict]]) -> None:
    agent = st.session_state.get("agent_sel")
    if not agent:
        st.caption("Click an agent to see what it found.")
        return
    st.markdown(f"**{ICON[agent]} {agent.capitalize()}**")
    if not by.get(agent):
        st.caption("No steps in this run.")
    for s in sorted(by.get(agent, []), key=lambda s: -RANK[s["status"]]):  # blocks and flags first
        c = COLOR[s["status"]]
        ev = "".join(f'<li>“{html.escape(e["text"])}” <i>({html.escape(e["technique"])}, {html.escape(e["field"])})</i></li>'
                     for e in s["evidence"])
        st.html(f'<div style="border-left:4px solid {c};padding:0.3rem 0.7rem;margin:0.3rem 0;font-size:1rem">'
                f'<b style="color:{c}">{s["status"].upper()}</b> · {html.escape(s["call"])} · {s["ms"]} ms<br>'
                f'{html.escape(s["summary"])}{f"<ul>{ev}</ul>" if ev else ""}</div>')
