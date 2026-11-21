"""B1: session state the firewall tracks: what the user asked for, and what the agent has read since."""
import re
import uuid
from typing import Optional, TypedDict

from shared.contracts import ToolCall, ToolResult

REPO_RE = re.compile(r"\b[\w.-]+/[\w.-]+\b")


class Session(TypedDict):
    id: str
    user_request: str
    mentioned_repos: list[str]      # e.g. ["alice/public-site"]
    tainted: bool                   # True once the agent has read untrusted content
    taint_sources: list[dict]       # {"source", "author", "repo"}
    private_reads: list[dict]       # {"repo", "path", "text"}
    findings: list[dict]            # scanner evidence: {"where", "field", "text", "technique", ...}


def new_session(user_request: str) -> Session:
    # rstrip: "alice/public-site." at the end of a sentence must not keep the dot
    repos = [r.rstrip(".") for r in REPO_RE.findall(user_request)]
    return {"id": uuid.uuid4().hex[:8], "user_request": user_request, "mentioned_repos": list(dict.fromkeys(repos)),
            "tainted": False, "taint_sources": [], "private_reads": [], "findings": []}


def record_result(session: Session, call: ToolCall, result: ToolResult) -> None:
    p = result["provenance"]
    if not p["trusted"]:
        session["tainted"] = True
        session["taint_sources"].append({"source": p["source"], "author": p["author"], "repo": p["repo"]})
    if p["visibility"] == "private":
        path: Optional[str] = call["args"].get("path")
        session["private_reads"].append({"repo": p["repo"], "path": path, "text": str(result["output"])})
