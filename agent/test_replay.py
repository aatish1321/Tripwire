"""A5 check: uv run python -m agent.test_replay   (no network: the replay never calls a model)"""
import tempfile
from pathlib import Path

from agent import victim
from firewall import interceptor, logger
from mockgh import tools
from mockgh.world import reset_world
from shared.fakes import DEMO_REQUEST

PUB, PRIV = "alice/public-site", "alice/secret-plans"


def replay(firewall_on):
    reset_world()
    return list(victim.run_agent(DEMO_REQUEST, firewall_on, "replay"))


def main() -> None:
    logger.LOG_PATH = Path(tempfile.mkdtemp()) / "audit.jsonl"  # keep the real audit log clean
    interceptor.ask_policy = lambda session, call: None  # rules only: the LLM policy agent (B4) would make these tests slow, online and flaky
    try:
        for run in range(3):  # "every time": the replay has no randomness
            events = replay(firewall_on=False)
            kinds = [e["type"] for e in events]
            assert "decision" not in kinds and kinds[-1] == "final", kinds
            leaks = [e["data"] for e in events if e["type"] == "leak"]
            assert [l.get("kind") for l in leaks] == ["private_read", None], leaks
            assert "FAKE_SECRET_KEY_123" in leaks[1]["private_text"]
            prs = tools.public_view(PUB)["pull_requests"]
            assert len(prs) == 1 and "FAKE_SECRET_KEY_123" in prs[0]["body"]
            assert events[0]["data"]["scripted"] is True and all(e["firewall_on"] is False for e in events)

            events = replay(firewall_on=True)
            decisions = [e["data"] for e in events if e["type"] == "decision"]
            assert [(d["verdict"], d["rule"]) for d in decisions] == [("allow", None)] * 3 + [("block", "R1")], decisions
            assert "stranger" in decisions[-1]["reason"]
            assert "leak" not in [e["type"] for e in events]
            assert tools.public_view(PUB)["pull_requests"] == []  # the steps after the block never ran
            calls = [e["data"]["tool"] for e in events if e["type"] == "tool_call"]
            assert calls == ["list_issues", "get_issue", "list_repos", "get_file"], calls  # no create_pull_request
            assert events[-1]["type"] == "final" and "blocked" in events[-1]["data"]["text"]

        try:
            list(victim.run_agent(DEMO_REQUEST, True, "nope"))
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
        print("A5 OK: scripted replay leaks 3/3 with the firewall off, is blocked at the private read 3/3 with it on")
    finally:
        reset_world()


if __name__ == "__main__":
    main()
