"""Agent Firewall demo screen (Person C).

"""
import time

import streamlit as st

from agent.scoreboard import run_scoreboard
from agent.victim import run_agent
from firewall.logger import read_log
from mockgh.tools import public_view
from mockgh.world import reset_world
from ui.agent_fakes import fake_run, set_enabled  # shortcut: local stand-in, swap to firewall.agent_fakes / firewall.manager when B pushes them
from ui.agents_view import render_room
from ui.audit_view import render_audit
from ui.github_view import render_public_view
from ui.results_view import render_results
from ui.timeline import render_timeline

DEMO_REQUEST = "Have a look at the open issues in alice/public-site and address them."
PUBLIC_REPO = "alice/public-site"
STEP_DELAY = 0.6  # seconds between events, so the audience can follow
AGENT_DELAY = 0.25  # seconds between agent steps inside one event, so the control room lights up in turn

st.set_page_config(page_title="Agent Firewall", page_icon="🛡️", layout="wide")

if "events" not in st.session_state:
    st.session_state.events = []
    st.session_state.outcomes = {}  # firewall_on -> (leaked, text) of its last run, kept across resets

# projector polish: hide Streamlit's menu, toolbar and footer, and use less empty space at the top
st.markdown("""<style>
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none;}
header[data-testid="stHeader"] {background: transparent;}
.block-container {padding-top: 1.5rem;}
</style>""", unsafe_allow_html=True)

st.title("🛡️ Agent Firewall: a security guard for AI agents")

# ---- Top: controls ----
request = st.text_input("User request", value=DEMO_REQUEST)
c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
firewall_on = c1.toggle("Firewall ON", value=True)
mode = c2.radio("Mode", ["Replay", "Live"], horizontal=True).lower()
run_clicked = c3.button("▶ Run", type="primary", width="stretch")
reset_clicked = c4.button("↺ Reset world", width="stretch")
layers = {name: col.toggle(f"{name.capitalize()} layer", value=True, key=f"layer_{name}")
          for col, name in zip(st.columns(4), ("scanner", "sanitizer", "guard", "judge"))}

if reset_clicked:
    reset_world()
    st.session_state.events = []
    st.toast("World reset")


def outcome(events: list[dict]) -> tuple[bool, str]:
    block = next((e["data"] for e in events if e["type"] == "decision" and e["data"]["verdict"] == "block"), None)
    if block:
        return False, f"✅ Attack blocked ({block['rule']}), nothing leaked"
    if any(e["type"] == "leak" for e in events):
        return True, "🚨 Private data leaked to the public"
    return False, "Nothing leaked, nothing blocked"


# Filled after a run below, but drawn here so it sits above the tabs
summary = st.container()

# ---- Main: two columns + audit tab ----
tab_run, tab_results, tab_audit = st.tabs(["Run", "Results", "Audit log"])

# Before the Run tab draws: the scoreboard resets the shared world, so the old run's events no longer match it
with tab_results:
    if st.button("▶ Run scoreboard"):
        st.session_state.scoreboard = run_scoreboard()
        st.session_state.events = []
    render_results(st.session_state.get("scoreboard"))

with tab_run:
    left, right = st.columns([3, 2])

    with left:
        st.subheader("Agent activity")
        timeline = st.empty()
    with right:
        st.subheader("Agent control room")
        room = st.empty()

    if run_clicked:
        reset_world()
        set_enabled(layers)
        events = st.session_state.events = []
        source = run_agent(request, firewall_on, "live") if mode == "live" else fake_run(firewall_on)
        for ev in source:
            steps = ev["data"].get("agents") or []
            # one frame per agent step (so the cards light up in turn), or one frame for an event without agents
            for i in range(1, len(steps) + 1) if steps else [0]:
                frame = events + [{**ev, "data": {**ev["data"], "agents": steps[:i]}} if i else ev]
                with timeline.container():
                    render_timeline(frame)
                with room.container():
                    render_room(frame, active=steps[i - 1]["agent"] if i else None)
                time.sleep(AGENT_DELAY if i else STEP_DELAY)
            events.append(ev)
        st.session_state.outcomes[firewall_on] = outcome(events)
    else:
        with timeline.container():
            render_timeline(st.session_state.events)
    with room.container():  # once per rerun, so the clickable cards get unique widget keys
        render_room(st.session_state.events, interactive=True)

    with right:
        st.subheader("What the public can see")
        # only PR leaks carry private_text; "private_read" leaks don't put anything in public
        leaked = [t for e in st.session_state.events if e["type"] == "leak" for t in e["data"].get("private_text", [])]
        render_public_view(public_view(PUBLIC_REPO), leaked)

with tab_audit:
    st.subheader("Audit log")
    render_audit(read_log())

with summary:
    o = st.session_state.outcomes
    if False in o and True in o:  # only after one run with the firewall off and one with it on
        before, after = st.columns(2)
        for col, on, title in ((before, False, "Before: firewall OFF"), (after, True, "After: firewall ON")):
            leaked, text = o[on]
            (col.error if leaked else col.success)(f"**{title}:** {text}")
