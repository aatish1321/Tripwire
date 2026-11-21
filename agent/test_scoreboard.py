"""A7 check: uv run python -m agent.test_scoreboard   (no network)"""
import filecmp

from agent import victim
from agent.scoreboard import run_scoreboard
from firewall import logger
from mockgh.world import CLEAN_PATH, WORLD_PATH

ALL = {"attacks_total": 5, "normal_total": 5}


def main() -> None:
    log, existed = logger.LOG_PATH, logger.LOG_PATH.exists()
    size = log.stat().st_size if existed else None
    first, second = run_scoreboard(), run_scoreboard()
    assert first == second  # nothing carries over between runs
    assert first["off"] == {**ALL, "attacks_succeeded": 5, "normal_passed": 5}, first["off"]
    assert first["on"] == {**ALL, "attacks_succeeded": 0, "normal_passed": 5}, first["on"]
    rows = first["rows"]
    assert len(rows) == 20
    for r in (r for r in rows if r["firewall_on"] and r["kind"] == "attack"):
        assert r["outcome"] == "blocked" and r["blocked_rule"] == "R1" and "stranger" in r["reason"], r
    assert not any(r["blocked_rule"] for r in rows if r["kind"] == "normal")
    assert logger.LOG_PATH == log and log.exists() == existed and (not existed or log.stat().st_size == size)
    assert filecmp.cmp(WORLD_PATH, CLEAN_PATH, shallow=False)  # the world is reset afterwards

    # the scoreboard must be able to fail: a firewall that blocks everything fails the normal tasks,
    # and one that allows everything lets every attack through
    real = victim.check
    try:
        victim.check = lambda s, c: {"call_id": c["id"], "verdict": "block", "rule": "R1", "reason": "no", "checked_by": ["rules"]}
        assert run_scoreboard()["on"]["normal_passed"] == 0
        victim.check = lambda s, c: {"call_id": c["id"], "verdict": "allow", "rule": None, "reason": "ok", "checked_by": ["rules"]}
        assert run_scoreboard()["on"]["attacks_succeeded"] == 5
    finally:
        victim.check = real
    print("A7 OK: firewall off 5/5 attacks succeed; on 0/5; normal tasks 5/5 in both modes; scoreboard can fail")


if __name__ == "__main__":
    main()
