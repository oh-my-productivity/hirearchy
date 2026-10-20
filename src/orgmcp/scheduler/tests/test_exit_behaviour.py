# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import time

import pytest
from testkit.legacy.orgmcp.core import ROOT

from orgmcp.scheduler import EXIT_FILE, Scheduler, describe_scheduler, waiting_on_user
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


def test_serve_until_done_exits_when_budget_stalled_and_records_the_reason(org, stalled_on_budget):
    lines = []
    Scheduler(org, never_runner, echo=lines.append, clock=Clock(step=40)).serve(until_done=True)
    reason = 'waiting on you: "Rework the report" needs budget (ceo out of runs)'
    assert f"scheduler exiting: {reason}" in lines
    assert (org.root / EXIT_FILE).read_text().strip() == reason
    assert not (org.root / ".runtime" / "scheduler.pid").exists()
    assert describe_scheduler(org) == f"scheduler: stopped ({reason})"


def test_serve_until_done_exits_when_a_worker_keeps_failing(org):
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=5)
    org.pause("ceo", "failures")
    lines = []
    Scheduler(org, never_runner, echo=lines.append, clock=Clock(step=40)).serve(until_done=True)
    assert any(x.startswith("scheduler exiting: waiting on you:") and "resume ceo" in x for x in lines)


def test_serve_without_until_done_keeps_going(org, stalled_on_budget):
    sched = Scheduler(org, never_runner, echo=lambda _: None, clock=Clock(step=40))
    waiting = Waiting(sched)
    sched.acquire()
    try:
        for _ in range(12):  # well past the grace period
            sched.tick()
            assert waiting() in ("", sched.waiting_on_user().text)
    finally:
        sched.release()
    assert not (org.root / EXIT_FILE).exists()


def test_a_plain_stall_waits_for_the_stall_ladder_before_the_exit(org):
    """No pause, no budget problem: ceo holds the task and does nothing. The reminders (stall_after) come first."""
    task = org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=5)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)  # read it, never reports
    clock = Clock()
    waiting = Waiting(Scheduler(org, never_runner, echo=lambda _: None, clock=clock))
    w = waiting_on_user(org)
    assert w.text == 'waiting on you: "Ship it" needs a decision (ceo holds it and nothing is running)' and not w.settled
    waiting()
    clock.t += 5000
    assert waiting() == ""  # not told root yet: the ladder may still wake ceo
    org.save_ledger("nudges", {task.id: {"step": 0, "at": clock.t}})  # reminded
    assert waiting() == ""
    org.save_ledger("nudges", {task.id: {"step": 1, "at": clock.t}})  # root told: nothing else will happen
    assert waiting_on_user(org).settled
    assert waiting().startswith('waiting on you: "Ship it" needs a decision')
