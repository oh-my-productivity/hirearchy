"""``RunnableOpenWork``: whether anything is left to do (moved from ``scheduler.nothing_to_do``)."""

from __future__ import annotations

from collections.abc import Collection

from ..eligibility import RunnableQuery
from ..kernel import ROOT
from ..mail import TaskQuery
from .api import OpenWork


class RunnableOpenWork(OpenWork):
    def __init__(self, tasks: TaskQuery, runnable: RunnableQuery) -> None:
        self._tasks = tasks
        self._runnable = runnable

    def nothing_to_do(self, *, running: Collection[str] = (), blocked: Collection[str] = (), can_start: bool = True) -> bool:
        return not self._tasks.outstanding(ROOT) and not running and not (can_start and self._runnable.runnable(exclude=set(running) | set(blocked)))
