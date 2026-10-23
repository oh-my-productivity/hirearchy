"""A throttled run under the real loop (phase 0a.2, design 9.2 and 9.3): the fake agent of the testkit prints the throttle lines and exits 75."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import testkit
from testkit.reach.hirearchy.core import ROOT, Message, Org
from testkit.scheduler_loop import Runner, loop_over

from hirearchy.kernel import is_run_credit, join_frontmatter, split_frontmatter

FAKE = str(testkit.FAKE_AGENT)
LINES = (
    "print('[run error] prompt: high traffic (code -32000): {\"errorType\":\"ModelThrottleError\",\"retryErrorType\":\"THROTTLING\"}');"
    "print('# kiro: throttled by the model service (retryErrorType THROTTLING); tool effects: none')"
)


def throttling(runs: int, target: str = "ceo") -> Runner:
    """The fake agent, throttled at its first ``runs`` runs when it is ``target``."""
    def build(org: Any, addr: str, prompt: str) -> tuple[list[str], Any, dict[str, str]]:
        env = {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": "work"}
        if addr == target:
            env["FAKE_THROTTLE_RUNS"] = str(runs)
        return [sys.executable, FAKE], org.dir(addr), env

    return build


def inline(code: str) -> Runner:
    """Every run executes ``code`` (python) with the agent's environment."""
    def build(org: Any, addr: str, prompt: str) -> tuple[list[str], Any, dict[str, str]]:
        return [sys.executable, "-c", code], org.dir(addr), {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr}

    return build


def run_until_idle(org: Org, runner: Runner, max_ticks: int = 500) -> list[str]:
    said: list[str] = []
    sched = loop_over(org, runner, echo=said.append)
    sched.acquire()
    try:
        for _ in range(max_ticks):
            if not sched.tick():
                return said
            time.sleep(0.02)
        raise AssertionError("organization never went idle")
    finally:
        sched.release()


def credits(org: Org, addr: str = "ceo") -> list[Message]:
    return [m for m in org.received(addr) if is_run_credit(m)]


def failure_count(org: Org, addr: str = "ceo") -> int:
    path = Path(org.root) / ".runtime" / "failures.json"
    return int((json.loads(path.read_text()) if path.exists() else {}).get(addr, 0) or 0)


def configure(org: Org, **changes: object) -> None:
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


def test_one_throttle_is_credited_retried_and_not_a_failure(org: Org) -> None:
    task = org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    said = run_until_idle(org, throttling(1))

    (result,) = [m for m in org.received(ROOT) if m.type == "result"]
    assert result.reply_to == task.id and result.status == "done"  # the retry ran and finished
    assert len(credits(org)) == 1 and org.runs_used("ceo") == 3  # three logs, two charged: the budget after is the budget of a flow without the throttle
    assert result.budget == (6 - 2 + 1) - 2 and org.budget("ceo") == 0
    assert failure_count(org) == 0 and not [line for line in said if "run failed" in line]
    assert any(line == "ceo: run throttled by the model service before any tool effect: not charged, retried" for line in said)


def test_two_throttles_are_credited_and_one_failure_is_counted(org: Org) -> None:
    task = org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    said = run_until_idle(org, throttling(2))

    (result,) = [m for m in org.received(ROOT) if m.type == "result"]
    assert result.reply_to == task.id and result.status == "done" and result.budget == (6 - 2 + 1) - 2
    assert len(credits(org)) == 2  # both throttles are not charged
    assert [line for line in said if "run failed" in line] == ["ceo: run failed (1 in a row), log: " + next(line for line in said if "run failed" in line).split("log: ")[1]]
    assert failure_count(org) == 0  # the next run succeeded and cleared the count


def test_max_failures_0_pauses_at_the_first_counted_throttle(org: Org) -> None:
    configure(org, max_failures=0)
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    run_until_idle(org, throttling(5))
    assert org.paused("ceo") == "failures" and org.runs_used("ceo") == 2 and len(credits(org)) == 2  # the first is free, the second is counted
    assert any("keeps failing" in m.title for m in org.messages(ROOT, "inbox"))


def test_a_run_that_sends_before_the_throttle_is_charged(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=10)
    code = "import os\nfrom hirearchy.core import Org\nOrg(os.environ['ORG_ROOT']).send(os.environ['ORG_AGENT'], 'root', 'a note before the throttle')\n" + LINES + "\nraise SystemExit(75)\n"
    run_until_idle(org, inline(code))
    assert credits(org) == [] and org.paused("ceo") == "failures" and org.runs_used("ceo") == 3


def test_a_run_that_prints_the_lines_but_exits_1_is_charged(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=10)
    run_until_idle(org, inline(LINES + "\nraise SystemExit(1)\n"))
    assert credits(org) == [] and org.paused("ceo") == "failures" and org.runs_used("ceo") == 3
