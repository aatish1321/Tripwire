"""B1 test. Run: uv run python -m firewall.test_session"""
from firewall.session import new_session, record_result
from shared.fakes import DEMO_REQUEST, ISSUE_1, PRIVATE_README, fake_provenance_for

s = new_session(DEMO_REQUEST)
assert s["mentioned_repos"] == ["alice/public-site"], s["mentioned_repos"]
assert not s["tainted"] and s["private_reads"] == []

issue_call = {"id": "c1", "tool": "get_issue", "args": {"repo": "alice/public-site", "number": 1}, "step": 1}
record_result(s, issue_call, {"call_id": "c1", "output": ISSUE_1,
                              "provenance": fake_provenance_for("get_issue", issue_call["args"], ISSUE_1)})
assert s["tainted"] and s["taint_sources"] == [{"source": "issue", "author": "mallory", "repo": "alice/public-site"}]
assert s["private_reads"] == []

file_call = {"id": "c2", "tool": "get_file", "args": {"repo": "alice/secret-plans", "path": "README.md"}, "step": 2}
record_result(s, file_call, {"call_id": "c2", "output": PRIVATE_README,
                             "provenance": fake_provenance_for("get_file", file_call["args"], PRIVATE_README)})
assert len(s["taint_sources"]) == 1  # alice's own file does not add taint
assert s["private_reads"] == [{"repo": "alice/secret-plans", "path": "README.md", "text": PRIVATE_README}]

print("B1 OK: session is tainted by mallory and has 1 private read")
