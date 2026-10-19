"""What the pidfile and the process table say about the scheduler of an organization."""

from __future__ import annotations

from ..attention import WaitingOnUser
from ..kernel import OrgLayout
from ..mail import TaskQuery
from ..processes import ProcessInspector
from ._ports import Children, SchedulerRecognizer
from .api import ExitMarker, SchedulerState, SchedulerStatus


class PidFileSchedulerStatus(SchedulerStatus):
    def __init__(
        self,
        layout: OrgLayout,
        inspector: ProcessInspector,
        recognizer: SchedulerRecognizer,
        children: Children,
        marker: ExitMarker,
        tasks: TaskQuery,
        waiting: WaitingOnUser,
    ) -> None:
        self._layout = layout
        self._inspector = inspector
        self._recognizer = recognizer
        self._children = children
        self._marker = marker
        self._tasks = tasks
        self._waiting = waiting

    def state(self) -> SchedulerState:
        raise NotImplementedError

    def describe(self) -> str:
        raise NotImplementedError

    def exit_reason(self) -> str:
        raise NotImplementedError
