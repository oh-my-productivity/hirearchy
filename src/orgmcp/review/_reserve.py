"""``BudgetReserveCheck``: may a manager be written to (moved from ``review._cannot_afford``)."""

from __future__ import annotations

from ..budget import BudgetQuery
from ..eligibility import PauseStore
from ..mail import TaskQuery
from ._ports import ReserveCheck


class BudgetReserveCheck(ReserveCheck):
    def __init__(self, pauses: PauseStore, budgets: BudgetQuery, tasks: TaskQuery) -> None:
        self._pauses = pauses
        self._budgets = budgets
        self._tasks = tasks

    def why_not(self, manager: str) -> str:
        raise NotImplementedError("red: C-review")
