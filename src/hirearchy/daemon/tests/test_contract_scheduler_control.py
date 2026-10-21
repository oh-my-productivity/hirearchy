"""Contract of ``SchedulerControl``: start a detached scheduler, stop it, and never signal a process that is not this organization's scheduler.

Over a scripted process table, over the machine's processes (the scheduler it starts is a stand-in program; only that and the processes the test
started are ever signalled), and over the in-memory fake."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from hirearchy.daemon import SchedulerControl
from hirearchy.daemon.testing import IMPLEMENTATIONS, ControlWorld
from hirearchy.kernel import OrgError

from ._support import build, worlds


@pytest.fixture(params=worlds(IMPLEMENTATIONS[SchedulerControl]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[ControlWorld]:
    world = build(request, tmp_path, ControlWorld)
    assert isinstance(world.control, SchedulerControl)
    yield world
    world.close()


def test_start_returns_the_pid_of_a_scheduler_that_is_then_running(w: ControlWorld) -> None:
    pid = w.control.start()
    state = w.status.state()
    assert (state.state, state.pid) == ("running", pid)
    assert w.alive(pid)


def test_a_second_start_is_refused_and_names_the_running_one(w: ControlWorld) -> None:
    pid = w.control.start()
    with pytest.raises(OrgError, match=rf"a scheduler is already running for this org \(pid {pid}, since .+\); call stop\(\) first to restart it"):
        w.control.start()
    assert w.status.state().pid == pid


def test_a_negative_cap_is_refused_and_nothing_is_started(w: ControlWorld) -> None:
    with pytest.raises(OrgError, match="max_runs must be 0 or more"):
        w.control.start(-1)
    assert w.status.state().state == "stopped"


def test_a_cap_of_zero_and_until_done_are_allowed(w: ControlWorld) -> None:
    pid = w.control.start(0, True)
    assert w.status.state().pid == pid


def test_a_live_process_the_pidfile_names_but_that_is_not_a_scheduler_blocks_a_start(w: ControlWorld) -> None:
    pid = w.impostor()
    with pytest.raises(OrgError, match=rf"not starting: \.runtime/scheduler\.pid names pid {pid}, which is alive but not verified to be this org's scheduler \("):
        w.control.start()
    assert w.alive(pid)


def test_a_stale_pidfile_does_not_block_a_start(w: ControlWorld) -> None:
    stale = w.stale()
    pid = w.control.start()
    assert pid != stale and w.status.state().pid == pid


def test_stop_without_a_scheduler_says_so(w: ControlWorld) -> None:
    assert w.control.stop() == "no scheduler is running for this org"


def test_stop_ends_the_scheduler_and_says_when_it_has(w: ControlWorld) -> None:
    pid = w.control.start()
    assert w.control.stop() == f"scheduler stopped (pid {pid})"
    assert w.status.state().state == "stopped"


def test_stop_never_signals_a_process_that_is_not_the_scheduler(w: ControlWorld) -> None:
    pid = w.impostor()
    with pytest.raises(OrgError, match=rf"not signalling pid {pid}: it is alive but not verified to be this org's scheduler \(.+\)\. If it is, stop it yourself \(kill {pid}\)"):
        w.control.stop()
    assert w.alive(pid)


def test_a_scheduler_can_be_started_again_after_it_was_stopped(w: ControlWorld) -> None:
    first = w.control.start()
    w.control.stop()
    second = w.control.start()
    assert second != first and w.status.state().pid == second
    assert re.fullmatch(rf"scheduler stopped \(pid {second}\)", w.control.stop())
