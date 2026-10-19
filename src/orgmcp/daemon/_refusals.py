"""What is refused when the pidfile names a scheduler that runs, or a process that cannot be trusted - one text for the real control and its fake."""

from __future__ import annotations

from .api import SchedulerState

NO_SCHEDULER = "no scheduler is running for this org"
SINCE_FORMAT = "%Y-%m-%d %H:%M:%SZ"  # how ``SchedulerState.since`` is written


def check_startable(state: SchedulerState) -> None:
    """Raise ``OrgError`` when starting a scheduler would be wrong: one runs already, or a live process the pidfile names is not trusted."""
    raise NotImplementedError


def check_stoppable(state: SchedulerState) -> None:
    """Raise ``OrgError`` when the pidfile names a live process that is not verified to be this organization's scheduler: it is never signalled."""
    raise NotImplementedError
