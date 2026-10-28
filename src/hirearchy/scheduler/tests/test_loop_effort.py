"""A run stopped at kiro-cli's effort warning under the real loop (batch 1.1, design 2.4 and 5): the fake agent of the testkit prints the launcher's
mark and kills itself (exit -9), as the launcher's group kill does."""

from __future__ import annotations

import os
import sys
from typing import Any

import testkit
from testkit.reach.hirearchy.core import ROOT, Org
from testkit.scheduler_loop import Runner

from .test_loop_throttle import credits, failure_count, run_until_idle

FAKE = str(testkit.FAKE_AGENT)


def effort_stopping(runs: int, target: str = "ceo") -> Runner:
    """The fake agent, stopped at its first ``runs`` runs when it is ``target``."""
    def build(org: Any, addr: str, prompt: str) -> tuple[list[str], Any, dict[str, str]]:
        env = {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": "work"}
        if addr == target:
            env["FAKE_EFFORT_STOP_RUNS"] = str(runs)
        return [sys.executable, FAKE], org.dir(addr), env

    return build


def test_one_effort_stop_is_credited_relaunched_and_not_a_failure(org: Org) -> None:
    task = org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    said = run_until_idle(org, effort_stopping(1))

    (result,) = [m for m in org.received(ROOT) if m.type == "result"]
    assert result.reply_to == task.id and result.status == "done"  # the relaunch ran and finished
    assert len(credits(org)) == 1 and org.runs_used("ceo") == 3  # three logs, two charged
    assert result.budget == (6 - 2 + 1) - 2 and org.budget("ceo") == 0
    assert failure_count(org) == 0 and not [line for line in said if "run failed" in line]
    assert "ceo: run stopped because kiro-cli did not set its effort: not charged, relaunched" in said


def test_progress_leaves_the_effort_stopped_run_out(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    runner = effort_stopping(1)

    def idle_after_the_stop(org: Any, addr: str, prompt: str) -> tuple[list[str], Any, dict[str, str]]:
        argv, cwd, env = runner(org, addr, prompt)
        return argv, cwd, {**env, "FAKE_MODE": "idle"}  # the relaunch does nothing: the task stays open

    run_until_idle(org, idle_after_the_stop)
    assert org.runs_used("ceo") == 2 and len(credits(org)) == 1  # two logs, one of them credited
    assert "runs 1 of 6" in org.runtime.progress_reporter.progress()


def test_a_streak_of_effort_stops_pauses_the_agent_after_max_failures_plus_one(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=12)
    run_until_idle(org, effort_stopping(9))
    assert org.paused("ceo") == "failures" and org.runs_used("ceo") == 4 and len(credits(org)) == 4  # the first credit is free, the next three are counted
    assert any("keeps failing" in m.title for m in org.messages(ROOT, "inbox"))
