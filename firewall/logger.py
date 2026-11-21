"""B3: audit trail. One AuditEntry per decision, appended to logs/audit.jsonl."""
import json
from datetime import datetime, timezone
from pathlib import Path

from firewall.session import Session
from shared.contracts import AuditEntry, Decision, ToolCall

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "audit.jsonl"


def log_decision(session: Session, call: ToolCall, decision: Decision) -> None:
    entry: AuditEntry = {"ts": datetime.now(timezone.utc).isoformat(), "session_id": session["id"],
                         "user_request": session["user_request"], "call": call, "decision": decision}
    LOG_PATH.parent.mkdir(exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def read_log(session_id: str | None = None) -> list[AuditEntry]:
    if not LOG_PATH.exists():
        return []
    entries = [json.loads(line) for line in LOG_PATH.read_text().splitlines() if line.strip()]
    return [e for e in entries if session_id is None or e["session_id"] == session_id]
