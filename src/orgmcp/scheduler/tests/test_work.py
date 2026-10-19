"""What is left to do, from the standpoint of a scheduler: its runs in flight, the agents its orphans block and the cap on the runs it starts."""

from __future__ import annotations

from orgmcp.attention import Waiting
from orgmcp.attention.testing import FixedOpenWork, FixedWaiting
from orgmcp.processes.testing import FakeProcessTable
from orgmcp.kernel.testing import FakeClock
from orgmcp.scheduler._run import RunRecord, Standing
from orgmcp.scheduler._work import QueriedWork
from orgmcp.scheduler.testing import FixedRunnable

from ._support import a_run, red

pytestmark = red


def make(*runnable: str, idle: bool = False, waiting: Waiting | None = None) -> tuple[QueriedWork, FixedOpenWork, FixedRunnable, FixedWaiting]:
    work, queryable, analysis = FixedOpenWork(idle), FixedRunnable(*runnable), FixedWaiting(waiting)
    return QueriedWork(work, queryable, analysis), work, queryable, analysis


def a_run_of(addr: str) -> dict[str, RunRecord]:
    clock = FakeClock()
    return {addr: a_run(FakeProcessTable(clock), clock, addr)}


def test_a_run_in_flight_is_work_without_asking_who_could_start() -> None:
    work, _, runnable, _ = make("ops")
    assert work.remains(Standing(a_run_of("ceo"), set())) is True
    assert runnable.asked == []


def test_an_agent_that_could_start_is_work_while_the_cap_allows_a_run() -> None:
    work, _, runnable, _ = make("ops")
    assert work.remains(Standing({}, set(), can_start=True)) is True
    assert work.remains(Standing({}, set(), can_start=False)) is False
    assert runnable.asked == [frozenset(), frozenset()]


def test_nobody_who_could_start_and_nothing_in_flight_is_no_work() -> None:
    work, _, _, _ = make()
    assert work.remains(Standing({}, set())) is False


def test_the_agents_blocked_by_an_orphan_do_not_count() -> None:
    work, _, runnable, _ = make("ceo")
    assert work.remains(Standing({}, {"ceo"})) is False
    assert runnable.asked == [frozenset({"ceo"})]


def test_finished_is_the_open_work_port_asked_with_the_view_of_the_scheduler() -> None:
    work, open_work, _, _ = make(idle=True)
    assert work.finished(Standing(a_run_of("ceo"), {"ops"}, can_start=False)) is True
    assert open_work.asked == [({"ceo"}, {"ops"}, False)]


def test_not_finished_when_the_port_says_there_is_work() -> None:
    work, _, _, _ = make(idle=False)
    assert work.finished(Standing({}, set())) is False


def test_waiting_is_the_analysis_with_the_view_of_the_scheduler() -> None:
    found = Waiting("waiting on you: x", "Your options: y")
    work, _, _, analysis = make(waiting=found)
    assert work.waiting(Standing(a_run_of("ceo"), {"ops"}, can_start=False)) is found
    assert analysis.asked == [({"ceo"}, {"ops"}, False)]
