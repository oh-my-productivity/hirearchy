"""``check_startable`` and ``check_stoppable``: what a scheduler that runs, or a process that cannot be trusted, refuses."""

from __future__ import annotations

import pytest

from orgmcp.daemon import SchedulerState
from orgmcp.daemon._refusals import NO_SCHEDULER, SINCE_FORMAT, check_startable, check_stoppable
from orgmcp.kernel import OrgError


RUNNING = SchedulerState("running", 4242, "2026-10-18 10:00:00Z")
UNVERIFIED = SchedulerState("unverified", 4242, "2026-10-18 10:00:00Z", "its command line is 'vim'")


def test_a_stopped_scheduler_may_be_started() -> None:
    check_startable(SchedulerState("stopped"))


def test_a_running_scheduler_may_not_be_started_again() -> None:
    with pytest.raises(OrgError) as raised:
        check_startable(RUNNING)
    assert str(raised.value) == "a scheduler is already running for this org (pid 4242, since 2026-10-18 10:00:00Z); call stop() first to restart it"


def test_a_process_that_cannot_be_trusted_blocks_a_start() -> None:
    with pytest.raises(OrgError) as raised:
        check_startable(UNVERIFIED)
    assert str(raised.value) == (
        "not starting: .runtime/scheduler.pid names pid 4242, which is alive but not verified to be this org's scheduler "
        "(its command line is 'vim'). Check that process; if it is stale, remove that file"
    )


def test_a_running_scheduler_and_a_stopped_one_may_be_stopped() -> None:
    check_stoppable(RUNNING)
    check_stoppable(SchedulerState("stopped"))


def test_a_process_that_cannot_be_trusted_is_never_signalled() -> None:
    with pytest.raises(OrgError) as raised:
        check_stoppable(UNVERIFIED)
    assert str(raised.value) == (
        "not signalling pid 4242: it is alive but not verified to be this org's scheduler (its command line is 'vim'). If it is, stop it yourself (kill 4242)"
    )


def test_the_texts_other_modules_share() -> None:
    assert NO_SCHEDULER == "no scheduler is running for this org" and SINCE_FORMAT == "%Y-%m-%d %H:%M:%SZ"
