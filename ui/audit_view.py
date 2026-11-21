"""C4: audit log table from read_log(). Blocked rows in red."""
import pandas as pd
import streamlit as st


def render_audit(log: list[dict]) -> None:
    if not log:
        st.caption("No decisions yet.")
        return
    df = pd.DataFrame([{
        "time": e["ts"][11:19],  # HH:MM:SS from the ISO timestamp
        "tool": e["call"]["tool"],
        "verdict": e["decision"]["verdict"],
        "rule": e["decision"]["rule"] or "",
        "reason": e["decision"]["reason"],
    } for e in log])
    red = "background-color: rgba(255, 75, 75, 0.25)"
    styled = df.style.apply(lambda row: [red if row["verdict"] == "block" else ""] * len(row), axis=1)
    st.dataframe(styled, width="stretch", hide_index=True)
