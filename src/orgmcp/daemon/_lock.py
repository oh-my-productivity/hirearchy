"""The pidfile as the lock that keeps two schedulers off one organization."""

from __future__ import annotations

from ..kernel import OrgLayout
from ..processes import ProcessInspector
from .api import SchedulerLock


class PidFileSchedulerLock(SchedulerLock):
    def __init__(self, layout: OrgLayout, inspector: ProcessInspector) -> None:
        self._layout = layout
        self._inspector = inspector

    def acquire(self) -> None:
        raise NotImplementedError

    def release(self) -> None:
        raise NotImplementedError
