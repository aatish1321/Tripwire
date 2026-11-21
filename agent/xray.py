"""A13: the X-ray. Shows one text two ways: what a human sees on the page, and what the AI actually reads, with the
hidden parts marked (and decoded, for invisible text). Uses B's Scanner with its LLM pass off: same answer every time."""
import re

from firewall.sanitizer import INVISIBLE, LABEL
from firewall.scanner import scan
from mockgh.variants import hide_issue_1
from mockgh.world import load_world

# tricks that hide text from a human. Anything else the Scanner finds (e.g. an instruction aimed at the AI) is visible.
HIDDEN = {"invisible_characters", "zero_width_characters", "html_comment", "hidden_styling", "encoded_payload"}
# zero-width characters hide only themselves: the word around them is still on the page, so a human still reads it
HIDES_TEXT = HIDDEN - {"zero_width_characters"}
STRANGER = {"source": "issue", "author": "mallory", "trusted": False, "repo": "alice/public-site", "visibility": "public"}


def xray(text: str, provenance: dict = STRANGER) -> dict:
    """{"human": what a person reads, "segments": [...], "hidden_count", "techniques"}. Joining every segment's "text"
    gives back `text`. A segment is {"text", "kind": "plain"|"hidden"|"suspicious"} and, for flagged ones,
    "technique", "label" and (invisible text, base64) "decoded"."""
    spans: list[tuple[int, int, dict]] = []
    for f in scan(text, provenance, use_llm=False):
        start = text.find(f["text"])
        while start != -1 and any(start < e and s < start + len(f["text"]) for s, e, _ in spans):
            start = text.find(f["text"], start + 1)  # this occurrence is already claimed: take the next one
        if start != -1:
            spans.append((start, start + len(f["text"]), f))
    segments, cursor = [], 0
    for start, end, f in sorted(spans, key=lambda s: s[0]):
        if start > cursor:
            segments.append({"text": text[cursor:start], "kind": "plain"})
        seg = {"text": text[start:end], "kind": "hidden" if f["technique"] in HIDDEN else "suspicious",
               "technique": f["technique"], "label": LABEL.get(f["technique"], f["technique"])}
        if "decoded" in f:
            seg["decoded"] = f["decoded"]
        segments.append(seg)
        cursor = end
    if cursor < len(text):
        segments.append({"text": text[cursor:], "kind": "plain"})
    shown = "".join(s["text"] for s in segments if s.get("technique") not in HIDES_TEXT).translate(INVISIBLE)
    return {"human": re.sub(r"\n{3,}", "\n\n", shown).strip(), "segments": segments,
            "hidden_count": sum(s["kind"] == "hidden" for s in segments),
            "techniques": sorted({s["technique"] for s in segments if "technique" in s})}


def subject() -> dict:
    """The showpiece: issue #1 with its attack hidden, as {"label", "title", "author", "raw", **xray(raw)}."""
    world = load_world()
    hide_issue_1(world)  # in memory only
    issue = world["repos"]["alice/public-site"]["issues"][0]
    return {"label": f"Issue #{issue['number']} on alice/public-site", "title": issue["title"], "author": issue["author"],
            "raw": issue["body"], **xray(issue["body"])}
