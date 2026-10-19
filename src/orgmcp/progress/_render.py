"""The report: the lines of the listed tasks, then what needs the user (moved from ``progress._render``)."""

from __future__ import annotations

from datetime import datetime

from ..attention import HumanQueue
from ..kernel import Clock
from ._ports import ProgressText, RootTasks, TaskLines


class RootTaskReport(ProgressText):
    def __init__(self, roots: RootTasks, lines: TaskLines, queue: HumanQueue, clock: Clock) -> None:
        self._roots = roots
        self._lines = lines
        self._queue = queue
        self._clock = clock

    def render(self, task_id: str | None, now: datetime | None) -> str:
        raise NotImplementedError("red: C-progress")
