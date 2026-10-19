"""The one line that says whether the scheduler runs (``scheduler: ...``)."""

from __future__ import annotations

from collections.abc import Callable

from ..attention import WaitingOnUser
from .api import SchedulerState


def describe_state(state: SchedulerState, exit_reason: Callable[[], str], waiting: WaitingOnUser) -> str:
    """The text of ``SchedulerStatus.describe`` for ``state``; why a stopped scheduler stopped is asked of ``exit_reason``, then of ``waiting``,
    only when it is needed."""
    raise NotImplementedError
