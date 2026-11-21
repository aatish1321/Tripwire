"""Agent Firewall demo screen (Person C).

C1: skeleton wired to shared/fakes.py. C5 swaps these imports for the real modules.
"""
import time

import streamlit as st

from shared.fakes import DEMO_REQUEST
from shared.fakes import fake_public_view as public_view
from shared.fakes import fake_read_log as read_log
from shared.fakes import fake_reset_world as reset_world
from shared.fakes import fake_run_agent as run_agent
from ui.timeline import render_timeline

PUBLIC_REPO = "alice/public-site"
STEP_DELAY = 0.6  # seconds between events, so the audience can follow

st.set_page_config(page_title="Agent Firewall", page_icon="🛡️", layout="wide")

if "events" not in st.session_state:
    st.session_state.events = []

st.title("🛡️ Agent Firewall")

# ---- Top: controls ----
request = st.text_input("User request", value=DEMO_REQUEST)
c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
firewall_on = c1.toggle("Firewall ON", value=True)
mode = c2.radio("Mode", ["Replay", "Live"], horizontal=True).lower()
run_clicked = c3.button("▶ Run", type="primary", width="stretch")
reset_clicked = c4.button("↺ Reset world", width="stretch")

if reset_clicked:
    reset_world()
    st.session_state.events = []
    st.toast("World reset")


# ---- Main: two columns + audit tab ----
tab_run, tab_audit = st.tabs(["Run", "Audit log"])

with tab_run:
    left, right = st.columns([3, 2])

    with left:
        st.subheader("Agent activity")
        timeline = st.empty()
        if run_clicked:
            reset_world()
            st.session_state.events = []
            for ev in run_agent(request, firewall_on, mode):
                st.session_state.events.append(ev)
                with timeline.container():
                    render_timeline(st.session_state.events)
                time.sleep(STEP_DELAY)
        else:
            with timeline.container():
                render_timeline(st.session_state.events)

    with right:
        st.subheader("What the public can see")
        prs = public_view(PUBLIC_REPO)["pull_requests"]
        if not prs:
            st.caption(f"No pull requests on {PUBLIC_REPO}.")
        for pr in prs:
            st.markdown(f"**PR #{pr['number']}: {pr['title']}**")
            st.code(pr["body"])

with tab_audit:
    st.subheader("Audit log")
    log = read_log()
    if log:
        st.dataframe(
            [{"time": e["ts"], "tool": e["call"]["tool"], "verdict": e["decision"]["verdict"],
              "rule": e["decision"]["rule"], "reason": e["decision"]["reason"]} for e in log],
            width="stretch",
        )
    else:
        st.caption("No decisions yet.")
