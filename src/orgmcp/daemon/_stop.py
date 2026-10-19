"""Stopping the scheduler of an organization."""

from __future__ import annotations

from ..kernel import Clock
from ..processes import ProcessInspector, ProcessSignaller
from ._ports import Children, SchedulerStopper
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
        raise NotImplementedError
