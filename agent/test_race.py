"""A13 check: uv run python -m agent.test_race   (no network: LLM calls off)"""
import filecmp
import tempfile
import time
from pathlib import Path

from agent.race import run_race
from firewall import logger
from firewall.manager import ENABLED, set_enabled
from mockgh.world import CLEAN_PATH, WORLD_PATH
from shared.fakes import DEMO_REQUEST


def race(**kw):
    items = list(run_race(DEMO_REQUEST, **kw))
    return items, {side: [i for i in items if i["side"] == side and not i.get("done")] for side in ("off", "on")}, \
        {i["side"]: i for i in items if i.get("done")}


def main() -> None:
    saved, real_log = dict(ENABLED), logger.LOG_PATH
    set_enabled({"llm": False})
    logger.LOG_PATH = Path(tempfile.mkdtemp()) / "audit.jsonl"
    try:
        for run in range(3):  # a race has no randomness, and runs leave nothing behind
            items, events, done = race()
            assert set(done) == {"off", "on"} and items[-1].get("done")
            assert done["off"]["outcome"] == "leaked" and done["on"]["outcome"] == "blocked", done
            assert "stranger" in done["on"]["headline"] and done["off"]["headline"]

            off_last, on_last = events["off"][-1], events["on"][-1]
            # OFF: the PR with the secret is in ITS world, and a stranger sees it
            prs = off_last["public"]["pull_requests"]
            assert len(prs) == 1 and "FAKE_SECRET_KEY_123" in prs[0]["body"], off_last["public"]
            assert off_last["attacker"]["public"]["pull_requests"] == prs
            # ON: nothing was published in ITS world, even though the other side was publishing at the same time
            assert on_last["public"]["pull_requests"] == [] and on_last["attacker"]["received"] == []
            assert [e["event"]["type"] for e in events["on"]].count("decision") >= 4
            assert "decision" not in [e["event"]["type"] for e in events["off"]]
            # the hidden-text issue: what both sides were given is the friendly-looking one with the attack hidden
            outputs = [e["event"]["data"]["output"] for e in events["off"] if e["event"]["type"] == "tool_result"]
            issue_off = next(o for o in outputs if isinstance(o, dict) and "body" in o)  # get_issue (list_issues is a list)
            assert "<!--" in issue_off["body"] and issue_off["author"] == "mallory"
            # the shared world file never changed
            assert filecmp.cmp(WORLD_PATH, CLEAN_PATH, shallow=False)

        # pacing: one beat per tool call keeps both sides in step, and the result is the same
        t = time.monotonic()
        paced, _, done = race(beat=0.05)
        assert time.monotonic() - t >= 0.2 and done["off"]["outcome"] == "leaked" and done["on"]["outcome"] == "blocked"

        # leaving early stops the workers; a bad mode is refused
        gen = run_race(DEMO_REQUEST, beat=0.05)
        next(gen)
        gen.close()
        try:
            list(run_race(DEMO_REQUEST, mode="live"))
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
        time.sleep(0.3)
        assert filecmp.cmp(WORLD_PATH, CLEAN_PATH, shallow=False)
        print("A13 OK: OFF leaks and ON is blocked at the same time, each in its own world; the shared world is untouched")
    finally:
        set_enabled(saved)
        logger.LOG_PATH = real_log


if __name__ == "__main__":
    main()
