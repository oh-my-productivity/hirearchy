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
        """Why a note must not be sent to this manager ("" = it may be). A note costs a run; the runs a manager
        holds in reserve (one per outstanding delegation, to process the result) are not for review notes."""
        if self._pauses.paused(manager):
            return "paused"
        budget, owed = self._budgets.budget(manager) or 0, len(self._tasks.outstanding(manager))
        if budget <= 0:
            return "no budget left"
        if budget <= owed:
            return f"budget {budget} is reserved for {owed} outstanding delegation(s)"
        return ""
