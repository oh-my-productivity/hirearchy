"""``RunnableOpenWork``: whether anything is left to do (moved from ``scheduler.nothing_to_do``)."""

from __future__ import annotations

from ..eligibility import RunnableQuery
from ..kernel import ROOT
from ..mail import TaskQuery
from .api import OpenWork


class RunnableOpenWork(OpenWork):
    def __init__(self, tasks: TaskQuery, runnable: RunnableQuery) -> None:
        self._tasks = tasks
        self._runnable = runnable

    def nothing_to_do(self) -> bool:
        return not self._tasks.outstanding(ROOT) and not self._runnable.runnable()
