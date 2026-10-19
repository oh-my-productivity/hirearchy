"""``describe_state``: the line of ``scheduler: ...`` for a state, a reason and what waits for the user."""

from __future__ import annotations

import pytest

from orgmcp.attention import Waiting
from orgmcp.attention.testing import FixedWaiting
from orgmcp.daemon import SchedulerState
from orgmcp.daemon._describe import describe_state


def never() -> str:
    raise AssertionError("not needed")


def test_running() -> None:
    state = SchedulerState("running", 4242, "2026-10-18 10:00:00Z")
    assert describe_state(state, never, FixedWaiting()) == "scheduler: running (pid 4242, since 2026-10-18 10:00:00Z)"


def test_unverified() -> None:
    state = SchedulerState("unverified", 7, "2026-10-18 10:00:00Z", "its command line is 'vim'")
    assert describe_state(state, never, FixedWaiting()) == (
        "scheduler: unknown - .runtime/scheduler.pid names pid 7, which is alive but not verified to be this org's scheduler "
        "(its command line is 'vim'); not trusted"
    )


def test_stopped_without_a_reason() -> None:
    assert describe_state(SchedulerState("stopped"), lambda: "", FixedWaiting()) == "scheduler: stopped"


def test_stopped_with_the_reason_of_its_exit() -> None:
    waiting = FixedWaiting(Waiting("waiting on you: x", "o"))
    assert describe_state(SchedulerState("stopped"), lambda: "finished: no open tasks", waiting) == "scheduler: stopped (finished: no open tasks)"
    assert waiting.asked == []


def test_stopped_while_the_user_is_waited_for() -> None:
    waiting = FixedWaiting(Waiting("waiting on you: x", "o"))
    assert describe_state(SchedulerState("stopped"), lambda: "", waiting) == "scheduler: stopped (waiting on you: x)"
    assert waiting.asked == [(None, (), True)]
