"""What is refused when the pidfile names a scheduler that runs, or a process that cannot be trusted - one text for the real control and its fake."""

from __future__ import annotations

from ..kernel import OrgError
from .api import SchedulerState

NO_SCHEDULER = "no scheduler is running for this org"
SINCE_FORMAT = "%Y-%m-%d %H:%M:%SZ"  # how ``SchedulerState.since`` is written


def check_startable(state: SchedulerState) -> None:
    """Raise ``OrgError`` when starting a scheduler would be wrong: one runs already, or a live process the pidfile names is not trusted."""
    if state.state == "running":
        raise OrgError(f"a scheduler is already running for this org (pid {state.pid}, since {state.since}); call stop() first to restart it")
    if state.state == "unverified":
        raise OrgError(
            f"not starting: .runtime/scheduler.pid names pid {state.pid}, which is alive but not verified to be "
            f"this org's scheduler ({state.detail}). Check that process; if it is stale, remove that file"
        )


def check_stoppable(state: SchedulerState) -> None:
    """Raise ``OrgError`` when the pidfile names a live process that is not verified to be this organization's scheduler: it is never signalled."""
    if state.state == "unverified":
        raise OrgError(
            f"not signalling pid {state.pid}: it is alive but not verified to be this org's scheduler "
            f"({state.detail}). If it is, stop it yourself (kill {state.pid})"
        )
