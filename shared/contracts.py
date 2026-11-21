from typing import TypedDict, Literal, Optional, Any

class Provenance(TypedDict):
    source: Literal["user", "repo_file", "issue", "tool_meta"]
    author: Optional[str]          # e.g. "mallory"
    trusted: bool                  # True only for the user and for repos the user owns
    repo: Optional[str]            # "alice/secret-plans"
    visibility: Optional[Literal["public", "private"]]

class ToolCall(TypedDict):
    id: str                        # "c1", "c2", ...
    tool: str                      # "get_file"
    args: dict[str, Any]
    step: int

class ToolResult(TypedDict):
    call_id: str
    output: Any                    # what the tool returned
    provenance: Provenance

class Decision(TypedDict):
    call_id: str
    verdict: Literal["allow", "block"]
    rule: Optional[str]            # "R1", "R2", "R3" or None
    reason: str                    # one plain-language sentence for the screen
    checked_by: list[str]          # e.g. ["rules", "policy_agent"]

class RunEvent(TypedDict):
    type: Literal["user", "agent_text", "tool_call", "decision", "tool_result", "leak", "final", "error"]
    data: dict[str, Any]           # the ToolCall / Decision / ToolResult / text
    firewall_on: bool

class AuditEntry(TypedDict):
    ts: str                        # ISO time
    session_id: str
    user_request: str
    call: ToolCall
    decision: Decision
