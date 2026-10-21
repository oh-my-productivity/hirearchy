"""The reporter: progress, the scheduler line, and whether anything could move (moved from ``progress.describe_progress`` and ``work_in_flight``)."""

from __future__ import annotations

from datetime import datetime

from ..attention import WaitingOnUser
from ..daemon import SchedulerStatus
from ..kernel import ROOT
from ..mail import TaskQuery
from ._ports import ProgressView, Snapshots
from ._snapshot import moving
from .api import ProgressReporter


class DerivedProgressReporter(ProgressReporter):
    def __init__(self, view: ProgressView, snapshots: Snapshots, scheduler: SchedulerStatus, waiting: WaitingOnUser, tasks: TaskQuery) -> None:
        self._view = view
        self._snapshots = snapshots
        self._scheduler = scheduler
        self._waiting = waiting
        self._tasks = tasks

    def progress(self, task_id: str | None = None, now: datetime | None = None, *, wait_seconds: int = 0) -> str:
        return self._view.progress(task_id, now, wait_seconds=wait_seconds)

    def describe_progress(self, task_id: str | None = None, wait_seconds: int = 0) -> str:
        sched = self._scheduler.describe()
        stopped = not sched.startswith("scheduler: running")
        open_work = bool(self._tasks.outstanding(ROOT))
        waiting = self._waiting.analyze() if open_work else None
        note = ""
        if waiting is not None and sched.startswith(("scheduler: running", "scheduler: stopped")):
            if stopped:  # the line already says why ("stopped (waiting on you: ...)")
                sched += f" - nothing moves until you act. {waiting.options}"
            else:
                sched += f" - {waiting.text}. {waiting.options} A scheduler started with until_done exits by itself soon."
            if wait_seconds:
                wait_seconds, note = 0, "Not waiting: nothing can progress without you. "
        elif stopped and open_work:
            sched += " - open tasks do not move until it is started (start() or `hirearchy run`)"
            if wait_seconds:
                wait_seconds, note = 0, "Not waiting: no scheduler is running, so nothing will change. "
        elif stopped and wait_seconds and self.work_in_flight(task_id):  # e.g. a blocked task whose lead was just granted runs
            sched += " - agents have work they could do, but nothing moves until it is started (start() or `hirearchy run`)"
            wait_seconds, note = 0, "Not waiting: no scheduler is running, so nothing will change. "
        return f"{note}{self._view.progress(task_id, wait_seconds=wait_seconds)}\n{sched}"

    def work_in_flight(self, task_id: str | None = None) -> bool:
        return moving(self._snapshots.snapshot(task_id))
