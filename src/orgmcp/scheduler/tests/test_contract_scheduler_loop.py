"""Contract of ``SchedulerLoop``: a pass says whether work remains, ``finished`` says whether an until-done scheduler is done, ``serve`` returns when it is
asked to stop at idle or at done, the cap on runs holds, and ``run_once`` leaves nothing running. Over the real loop (on a world of in-memory ports)
and over the in-memory loop."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.scheduler import SchedulerLoop
from orgmcp.scheduler.testing import IMPLEMENTATIONS, LoopWorld


@pytest.fixture(params=IMPLEMENTATIONS[SchedulerLoop], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> LoopWorld:
    made = request.param(tmp_path)
    assert isinstance(made.loop, SchedulerLoop)
    return made


def test_an_organization_without_work_has_no_work_and_is_finished(w: LoopWorld) -> None:
    assert w.loop.tick() is False
    assert w.loop.finished() is True and w.started() == 0


def test_a_pass_starts_the_work_and_says_there_is_more_to_come(w: LoopWorld) -> None:
    w.give_work()
    assert w.loop.finished() is False
    assert w.loop.tick() is True and w.started() == 1
    assert w.loop.finished() is False


def test_when_the_runs_are_over_and_the_task_is_answered_nothing_remains_and_it_is_finished(w: LoopWorld) -> None:
    w.give_work()
    w.loop.tick()
    w.let_runs_end()
    w.finish_work()
    assert w.loop.tick() is False and w.loop.finished() is True


def test_an_open_task_keeps_the_scheduler_from_being_finished_even_when_nothing_runs(w: LoopWorld) -> None:
    w.give_work()
    w.loop.tick()
    w.let_runs_end()
    w.loop.tick()
    assert w.loop.finished() is False


def test_the_cap_on_runs_started_stops_the_work_from_remaining(w: LoopWorld) -> None:
    w.give_work()
    w.give_work()
    assert w.loop.tick(max_runs=1) is True and w.started() == 1
    w.let_runs_end()
    assert w.loop.tick(max_runs=1) is False and w.started() == 1  # the first run is over; the cap is spent, so the second agent never starts
    w.finish_work()
    assert w.loop.finished(max_runs=1) is True  # nothing runs and nobody could start: the cap is what makes it so


def test_serve_until_idle_returns_once_everything_is_done(w: LoopWorld) -> None:
    w.give_work()
    w.finish_work()
    w.loop.serve(until_idle=True)
    assert w.started() == 1 and w.loop.tick() is False


def test_serve_until_done_returns_once_the_task_is_answered(w: LoopWorld) -> None:
    w.give_work()
    w.finish_work()
    w.loop.serve(until_done=True)
    assert w.started() == 1 and w.loop.finished() is True


def test_serve_with_a_cap_starts_no_more_runs_than_it(w: LoopWorld) -> None:
    w.give_work()
    w.give_work()
    w.finish_work()
    w.loop.serve(until_idle=True, max_runs=1)
    assert w.started() == 1


def test_run_once_makes_a_pass_and_waits_for_its_runs(w: LoopWorld) -> None:
    w.give_work()
    w.loop.run_once()
    assert w.started() == 1
