"""Results tab: A7's scoreboard, every scripted attack and normal task with the firewall off vs on."""
import pandas as pd
import streamlit as st

ICON = {"succeeded": "🚨 succeeded", "blocked": "⛔ blocked", "failed": "✗ failed", "passed": "✅ passed"}


def render_results(result: dict | None) -> None:
    if not result:
        st.caption("Press Run scoreboard to replay every attack and normal task with the firewall off and on.")
        return
    for col, mode, title in zip(st.columns(2), ("off", "on"), ("Firewall OFF", "Firewall ON")):
        s = result[mode]
        col.subheader(title)
        col.metric("Attacks that succeeded", f"{s['attacks_succeeded']} / {s['attacks_total']}")
        col.metric("Normal tasks that passed", f"{s['normal_passed']} / {s['normal_total']}")
    on = {r["name"]: r for r in result["rows"] if r["firewall_on"]}
    df = pd.DataFrame([{
        "scenario": r["name"],
        "kind": r["kind"],
        "firewall off": ICON[r["outcome"]],
        "firewall on": ICON[on[r["name"]]["outcome"]],
        "blocked by": on[r["name"]]["blocked_rule"] or "",
    } for r in result["rows"] if not r["firewall_on"]])
    st.dataframe(df, width="stretch", hide_index=True)
    st.caption("Scripted tool calls; the tools and the firewall rules run for real (policy agent off).")
