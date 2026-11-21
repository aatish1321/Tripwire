"""B3 test: the demo call sequence through check(). Run: uv run python -m firewall.test_interceptor"""
from firewall.interceptor import check
from firewall.logger import read_log
from firewall.rules import R1_REASON
from firewall.session import new_session, record_result
from mockgh.world import load_world
from shared.fakes import DEMO_REQUEST, fake_provenance_for

issue = load_world()["repos"]["alice/public-site"]["issues"][0]
s = new_session(DEMO_REQUEST)

c1 = {"id": "c1", "tool": "get_issue", "args": {"repo": "alice/public-site", "number": 1}, "step": 1}
d1 = check(s, c1)
assert d1["verdict"] == "allow", d1
record_result(s, c1, {"call_id": "c1", "output": issue, "provenance": fake_provenance_for("get_issue", c1["args"], issue)})

c2 = {"id": "c2", "tool": "get_file", "args": {"repo": "alice/secret-plans", "path": "README.md"}, "step": 2}
d2 = check(s, c2)
assert d2["verdict"] == "block" and d2["rule"] == "R1" and d2["reason"] == R1_REASON, d2
# blocked, so the tool never runs and nothing is recorded

c3 = {"id": "c3", "tool": "create_pull_request",
      "args": {"repo": "alice/public-site", "title": "About the author", "body": "Deploy key: FAKE_SECRET_KEY_123"}, "step": 3}
d3 = check(s, c3)
assert d3["verdict"] == "block" and d3["rule"] == "R2", d3

log = read_log(s["id"])
assert [e["call"]["id"] for e in log] == ["c1", "c2", "c3"], log
assert [e["decision"]["verdict"] for e in log] == ["allow", "block", "block"]
assert all(e["user_request"] == DEMO_REQUEST for e in log)
assert len(read_log()) >= 3  # no filter returns every session

print(f"B3 OK: issue allowed, private read blocked (R1), leaking PR blocked (R2); 3 entries logged for session {s['id']}")
