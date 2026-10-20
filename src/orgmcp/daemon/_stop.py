"""Stopping the scheduler of an organization."""

from __future__ import annotations

from ..kernel import Clock, OrgError
from ..processes import ProcessDenied, ProcessGone, ProcessInspector, ProcessSignaller, ProcessTableError
from ._ports import Children, SchedulerStopper
from ._refusals import NO_SCHEDULER, check_stoppable
from .api import SchedulerStatus


class SignalSchedulerStopper(SchedulerStopper):
    def __init__(
        self, status: SchedulerStatus, signaller: ProcessSignaller, inspector: ProcessInspector, children: Children, clock: Clock
    ) -> None:
        self._status = status
        self._signaller = signaller
        self._inspector = inspector
        self._children = children
        self._clock = clock

    def stop(self, wait: float) -> str:
        """SIGTERM the org's scheduler (pid from the pidfile), only after checking that it is really that scheduler.

        The scheduler shuts down cleanly: runs in flight are interrupted (their batch is redelivered later).
        """
        state = self._status.state()
        if state.state == "stopped":
            return NO_SCHEDULER
        check_stoppable(state)
        assert state.pid is not None  # a scheduler that is not stopped has a pid
        try:
            self._signaller.terminate(state.pid)
        except ProcessGone:
            return f"scheduler (pid {state.pid}) was already gone"
        except ProcessDenied:
            raise OrgError(f"not allowed to signal pid {state.pid}")
        deadline = self._clock.time() + wait
        while self._clock.time() < deadline:
            self._children.reap()
            try:
                info = self._inspector.info(state.pid)
            except ProcessTableError:
                break
            if info is None or info.state.startswith("Z"):
                return f"scheduler stopped (pid {state.pid})"
            self._clock.sleep(0.1)
        return (
            f"sent SIGTERM to the scheduler (pid {state.pid}); it is still shutting down (it interrupts agent runs first). "
            "Check status() shortly"
        )
