"""B10 test: the "ask the human" verdict. Run: uv run python -m firewall.test_approvals   (no network)"""
import tempfile
import threading
import time
from pathlib import Path

import firewall.interceptor as ic
from firewall import approvals, logger
from firewall.approvals import answer, pending, wait_for_human
from firewall.manager import ENABLED, set_enabled
from firewall.session import new_session
from shared.fakes import DEMO_REQUEST

logger.LOG_PATH = Path(tempfile.mkdtemp()) / "audit.jsonl"  # keep the real audit log clean
DEFAULTS = dict(ENABLED)
set_enabled({"llm": False})


def tainted():
    s = new_session(DEMO_REQUEST)
    s["tainted"] = True
    s["taint_sources"].append({"source": "issue", "author": "mallory", "repo": "alice/public-site"})
    return s


def call(cid, tool, **args):
    return {"id": cid, "tool": tool, "args": args, "step": 1}


delete_named = call("c1", "delete_repo", repo="alice/public-site")          # R4: the user named this repo
read_secret = call("c2", "get_file", repo="alice/secret-plans", path="README.md")  # R1
pr = call("c3", "create_pull_request", repo="alice/public-site", title="About", body="Made by Alice.")

# off by default: nothing changes for loops that don't wait for an answer
assert ENABLED["ask"] is False
d = ic.check(tainted(), delete_named)
assert (d["verdict"], d["rule"]) == ("block", "R4") and pending() == []

set_enabled({"ask": True})
# R1 stays a hard block even with asking on
d = ic.check(tainted(), read_secret)
assert (d["verdict"], d["rule"]) == ("block", "R1"), d

# R4 asks; the guard and judge steps show "flag", and the question is open
s = tainted()
d = ic.check(s, delete_named)
assert (d["verdict"], d["rule"]) == ("ask", "R4") and d["reason"].endswith("Do you want to allow it?"), d
assert [x["status"] for x in d["agents"]] == ["ok", "flag", "flag"] and pending() == ["c1"]

# approve: the UI answers from another thread while the agent loop waits
threading.Timer(0.1, lambda: answer("c1", True)).start()
final = wait_for_human(s, delete_named, d, timeout=5)
assert final["verdict"] == "allow" and final["checked_by"][-1] == "human" and final["reason"].startswith("Approved by you")
assert final["agents"][-1]["status"] == "ok" and pending() == []
assert answer("c1", False) is False  # already answered: a second click changes nothing

# deny
d = ic.check(s, delete_named)
threading.Timer(0.1, lambda: answer("c1", False)).start()
final = wait_for_human(s, delete_named, d, timeout=5)
assert final["verdict"] == "block" and final["reason"].startswith("Denied by you"), final

# no answer in time = blocked; a late click finds nothing
d = ic.check(s, delete_named)
t = time.time()
final = wait_for_human(s, delete_named, d, timeout=0.3)
assert final["verdict"] == "block" and final["reason"].startswith("No answer within 0.3 seconds") and time.time() - t < 1
assert answer("c1", True) is False and pending() == []

# an answer that arrives before the loop starts waiting still counts
d = ic.check(s, delete_named)
assert answer("c1", True) is True
assert wait_for_human(s, delete_named, d, timeout=5)["verdict"] == "allow"

# POLICY (only the LLM objects) asks too
real = ic.ask_policy
ic.ask_policy = lambda s, c: {"matches_request": False, "instruction_source": "untrusted_content", "reason": "A stranger asked for this."}
set_enabled({"llm": True})
d = ic.check(tainted(), pr)
assert (d["verdict"], d["rule"]) == ("ask", "POLICY"), d
approvals.answer("c3", False)
ic.ask_policy = real

# every ask and every final answer is in the audit log
verdicts = [e["decision"]["verdict"] for e in logger.read_log()]
assert verdicts.count("ask") == 5 and "human" in logger.read_log()[-2]["decision"]["checked_by"], verdicts

set_enabled(DEFAULTS)
print("B10 OK: R4 and POLICY ask (off by default), R1 stays a hard block; approve, deny, timeout and late clicks work; all logged")
