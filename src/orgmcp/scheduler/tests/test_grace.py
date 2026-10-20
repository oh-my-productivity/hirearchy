# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import time

import pytest
from testkit.legacy.orgmcp.core import ROOT, Org
from testkit.scheduler_loop import GraceWaiting, loop_over


class Clock:
    """A fake clock for the scheduler: moves only when told (or by ``step`` on every reading)."""

    def __init__(self, step: float = 0.0):
        self.t, self.step = time.time(), step

    def __call__(self) -> float:
        self.t += self.step
        return self.t


def never_runner(org, addr, prompt):
    raise AssertionError(f"{addr} must not be started")


# ------------------------------------------------------------------------------- until-done: waiting on the user
@pytest.fixture
def stalled_on_budget(org):
    """root's only task sits with ceo, which has used its single run: the task is unread and cannot be served."""
    task = org.delegate(ROOT, "ceo", "Rework the report", "Fix it", "It is fixed", budget=1)
    org.start_run_log("ceo")  # the one run is gone
    assert org.budget("ceo") == 0 and org.unread("ceo") == 1
    return task


def test_grace_period_with_a_fake_clock(org, stalled_on_budget):
    clock, lines = Clock(), []
    sched = loop_over(org, never_runner, echo=lines.append, clock=clock)
    waiting = GraceWaiting(org, sched, lines.append, clock)
    assert waiting() == ""  # first sight: the count starts
    assert any("Exiting in 300s unless something changes" in x for x in lines)
    clock.t += 299
    assert waiting() == ""
    clock.t += 1
    assert waiting() == 'waiting on you: "Rework the report" needs budget (ceo out of runs)'


def test_a_change_restarts_the_grace_period(org, stalled_on_budget):
    clock = Clock()
    waiting = GraceWaiting(org, loop_over(org, never_runner, echo=lambda _: None, clock=clock), lambda _: None, clock)
    waiting()
    clock.t += 250
    org.send(ROOT, "ceo", "more", budget=1)  # the user acts: runnable
    assert waiting() == "" and waiting.since is None
    org.start_run_log("ceo")  # ...and it is stuck again
    clock.t += 100
    assert waiting() == "" and waiting.since is not None
    clock.t += 299
    assert waiting() == ""
    clock.t += 2
    assert waiting().startswith("waiting on you:")


def test_the_grace_is_configurable(tmp_path):
    o = Org.init(tmp_path / "o", "m", {"until_done_grace_seconds": 5, "poll_seconds": 0.05})
    o.hire(ROOT, "ceo", "Chief", "Run.")
    o.delegate(ROOT, "ceo", "T", "G", "A", budget=1)
    o.start_run_log("ceo")
    clock = Clock()
    waiting = GraceWaiting(o, loop_over(o, never_runner, echo=lambda _: None, clock=clock), lambda _: None, clock)
    waiting()
    clock.t += 5
    assert waiting().startswith("waiting on you:")
