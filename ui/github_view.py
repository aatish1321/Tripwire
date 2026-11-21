"""C3: "What the public can see": open PRs on the public repo, with leaked text highlighted."""
import html

import streamlit as st


def highlight(text: str, secrets: list[str]) -> str:
    """HTML-escape text, then wrap every leaked string in a red <mark>."""
    out = html.escape(text)
    for s in secrets:
        out = out.replace(html.escape(s), f'<mark style="background:#ff4b4b;color:white">{html.escape(s)}</mark>')
    return out


def render_public_view(view: dict, secrets: list[str]) -> None:
    """secrets: the leaked private strings from this run's leak events (empty = no leak)."""
    if secrets:
        st.error("PRIVATE DATA IS NOW PUBLIC", icon="🚨")
    prs = view["pull_requests"]
    if not prs:
        st.caption(f"No pull requests on {view['repo']}.")
    for pr in prs:
        with st.container(border=True):
            st.markdown(f"**PR #{pr['number']}: {pr['title']}**")
            st.markdown(
                # <br> because Streamlit's markdown collapses newlines even inside <pre>
                f'<div style="font-family:monospace;font-size:1.05rem">'
                f'{highlight(pr["body"], secrets).replace(chr(10), "<br>")}</div>',
                unsafe_allow_html=True,
            )


assert highlight("a <b> KEY", ["KEY"]) == 'a &lt;b&gt; <mark style="background:#ff4b4b;color:white">KEY</mark>'
