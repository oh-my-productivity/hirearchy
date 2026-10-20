# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import time

import pytest
from testkit.legacy.orgmcp.core import ROOT, Org

from orgmcp.scheduler import Scheduler
from orgmcp.scheduler._exit import GraceWait
from orgmcp.scheduler._legacy import FunctionClock
from orgmcp.scheduler._ports import Console
from orgmcp.scheduler._run import GraceMemory, Standing
from orgmcp.scheduler._work import QueriedWork


class Clock:
    """A fake clock for the scheduler: moves only when told (or by ``step`` on every reading)."""

    def __init__(self, step: float = 0.0):
        self.t, self.step = time.time(), step

    def __call__(self) -> float:
        self.t += self.step
        return self.t


def never_runner(org, addr, prompt):
    raise AssertionError(f"{addr} must not be started")


class Waiting:
    """The grace period of an until-done scheduler (what ``Scheduler._check_waiting`` was): ``waiting()`` is the exit reason once nothing has progressed
    without the user for ``until_done_grace_seconds``, else ''; ``waiting.since`` is when the count began. It looks at the scheduler's own runs, its blocked
    agents and its clock, over the ports of the org's runtime."""

    def __init__(self, sched):
        rt = sched.org.runtime
        self.sched, self.memory = sched, GraceMemory()
        console = type("Console", (Console,), {"say": lambda _, line: sched.echo(line)})()
        work = QueriedWork(rt.open_work, rt.runnable_query, rt.waiting_on_user)
        self.grace = GraceWait(work, rt.settings, FunctionClock(lambda: sched.clock()), console, self.memory)

    @property
    def since(self):
        return self.memory.since

    def __call__(self, max_runs=None):
        s = self.sched
        return self.grace.check(Standing(s.runs, s._blocked, max_runs is None or s.total_runs < max_runs))


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
    sched = Scheduler(org, never_runner, echo=lines.append, clock=clock)
    waiting = Waiting(sched)
    assert waiting() == ""  # first sight: the count starts
    assert any("Exiting in 300s unless something changes" in x for x in lines)
    clock.t += 299
    assert waiting() == ""
    clock.t += 1
    assert waiting() == 'waiting on you: "Rework the report" needs budget (ceo out of runs)'


def test_a_change_restarts_the_grace_period(org, stalled_on_budget):
    clock = Clock()
    waiting = Waiting(Scheduler(org, never_runner, echo=lambda _: None, clock=clock))
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
    waiting = Waiting(Scheduler(o, never_runner, echo=lambda _: None, clock=clock))
    waiting()
    clock.t += 5
    assert waiting().startswith("waiting on you:")
