"""The one line that says whether the scheduler runs (``scheduler: ...``)."""

from __future__ import annotations

from collections.abc import Callable

from ..attention import WaitingOnUser
from .api import SchedulerState


def describe_state(state: SchedulerState, exit_reason: Callable[[], str], waiting: WaitingOnUser) -> str:
    """The text of ``SchedulerStatus.describe`` for ``state``; why a stopped scheduler stopped is asked of ``exit_reason``, then of ``waiting``,
    only when it is needed."""
    if state.state == "running":
        return f"scheduler: running (pid {state.pid}, since {state.since})"
    if state.state == "unverified":
        return (
            f"scheduler: unknown - .runtime/scheduler.pid names pid {state.pid}, which is alive but not verified "
            f"to be this org's scheduler ({state.detail}); not trusted"
        )
    reason = exit_reason()
    if not reason:
        waiting_now = waiting.analyze()
        reason = waiting_now.text if waiting_now else ""
    return f"scheduler: stopped ({reason})" if reason else "scheduler: stopped"
