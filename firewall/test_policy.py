"""B4 test. Run: uv run python -m firewall.test_policy
Part 1 uses a stand-in policy agent; part 2 switches Gemini off; part 3 calls real Gemini if GEMINI_API_KEY is set."""
import os
import tempfile
import time
from pathlib import Path

import firewall.interceptor as ic
from firewall import logger, policy_agent
from firewall.rules import R1_REASON
from firewall.session import new_session
from shared.fakes import DEMO_REQUEST

read_secret = {"id": "c2", "tool": "get_file", "args": {"repo": "alice/secret-plans", "path": "README.md"}, "step": 2}
pr = {"id": "c3", "tool": "create_pull_request",
      "args": {"repo": "alice/public-site", "title": "About the author", "body": "Alice made this."}, "step": 3}
read_issue = {"id": "c1", "tool": "get_issue", "args": {"repo": "alice/public-site", "number": 1}, "step": 1}


def tainted():
    s = new_session(DEMO_REQUEST)
    s["tainted"] = True
    s["taint_sources"].append({"source": "issue", "author": "mallory", "repo": "alice/public-site"})
    return s


logger.LOG_PATH = Path(tempfile.mkdtemp()) / "audit.jsonl"  # keep the real audit log clean
real_ask = ic.ask_policy
asked = []

# 1. stand-in policy agent
ic.ask_policy = lambda s, c: asked.append(c["id"]) or {
    "matches_request": False, "instruction_source": "untrusted_content", "reason": "A stranger asked for this."}
d = ic.check(tainted(), read_secret)
assert (d["verdict"], d["rule"], d["reason"]) == ("block", "R1", "A stranger asked for this."), d
assert d["checked_by"] == ["rules", "policy_agent"]
d = ic.check(tainted(), pr)  # rules allow this harmless PR, the policy agent blocks it
assert (d["verdict"], d["rule"]) == ("block", "POLICY"), d
asked.clear()
d = ic.check(tainted(), read_issue)  # allowed read: the policy agent is not asked
assert d["verdict"] == "allow" and asked == [] and d["checked_by"] == ["rules"]

ic.ask_policy = lambda s, c: {"matches_request": True, "instruction_source": "user", "reason": "Fine."}
d = ic.check(new_session(DEMO_REQUEST), pr)
assert d["verdict"] == "allow" and d["checked_by"] == ["rules", "policy_agent"], d

# 2. both LLMs switched off: the rules still block, with the template reason
ic.ask_policy = real_ask
keys = {k: os.environ.pop(k, None) for k in ("GEMINI_API_KEY", "GROQ_API_KEY")}
d = ic.check(tainted(), read_secret)
assert (d["verdict"], d["rule"], d["reason"], d["checked_by"]) == ("block", "R1", R1_REASON, ["rules"]), d

# 2b. Gemini slow, Groq answers: Groq wins after the head start; nobody answers: None at the deadline
slow = lambda p, d: time.sleep(9) or "{}"
fast = lambda p, d: '{"matches_request": false, "instruction_source": "untrusted_content", "reason": "Groq says no."}'
real_gemini, real_groq = policy_agent._gemini, policy_agent._groq
os.environ.update(GEMINI_API_KEY="x", GROQ_API_KEY="x")
policy_agent._gemini, policy_agent._groq = slow, fast
t = time.time()
r = policy_agent.ask_policy(tainted(), read_secret)
assert r and r["provider"] == "groq" and r["reason"] == "Groq says no." and 2.5 < time.time() - t < 4, (r, time.time() - t)
policy_agent._groq = slow
t = time.time()
assert policy_agent.ask_policy(tainted(), read_secret) is None and 5.5 < time.time() - t < 7
policy_agent._gemini, policy_agent._groq = real_gemini, real_groq
for k, v in keys.items():
    os.environ.pop(k, None)
    if v:
        os.environ[k] = v
print("B4 OK (offline): policy reason used, POLICY block, Groq fallback, 6 s cap, rules block with LLMs off")

# 3. live: Gemini, then Groq if Gemini is slow
if keys["GEMINI_API_KEY"] or keys["GROQ_API_KEY"]:
    t = time.time()
    r = policy_agent.ask_policy(tainted(), read_secret)
    print(f"live ({time.time() - t:.1f}s): {r}")
    d = ic.check(tainted(), read_secret)
    assert d["verdict"] == "block" and d["rule"] == "R1"
    print(f"check(): {d['verdict']} {d['rule']} {d['checked_by']}\n  reason: {d['reason']}")
else:
    print("No LLM keys in .env: live part skipped")
