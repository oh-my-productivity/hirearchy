"""The reporter: progress, the scheduler line, and whether anything could move (moved from ``progress.describe_progress`` and ``work_in_flight``)."""

from __future__ import annotations

from datetime import datetime

from ..attention import WaitingOnUser
from ..daemon import SchedulerStatus
from ..mail import TaskQuery
from ._ports import ProgressView, Snapshots
from .api import ProgressReporter


class DerivedProgressReporter(ProgressReporter):
    def __init__(self, view: ProgressView, snapshots: Snapshots, scheduler: SchedulerStatus, waiting: WaitingOnUser, tasks: TaskQuery) -> None:
        self._view = view
        self._snapshots = snapshots
        self._scheduler = scheduler
        self._waiting = waiting
        self._tasks = tasks

    def progress(self, task_id: str | None = None, now: datetime | None = None, *, wait_seconds: int = 0) -> str:
        raise NotImplementedError("red: C-progress")

    def describe_progress(self, task_id: str | None = None, wait_seconds: int = 0) -> str:
        raise NotImplementedError("red: C-progress")

    def work_in_flight(self, task_id: str | None = None) -> bool:
        raise NotImplementedError("red: C-progress")
