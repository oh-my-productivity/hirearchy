"""The reserve rule of every hand-down of runs (moved from ``Org._check_allocation``, ``Org._default_budget`` and ``Org._budget_to_return``)."""

from __future__ import annotations

from typing import SupportsInt, cast

from ..kernel import ROOT, Message, OrgError, latest_results, parent
from ..mail import MailboxReader, TaskQuery, moved_past
from ..settings import OrgSettings
from .api import AllocationPolicy, BudgetQuery


class ReserveAllocationPolicy(AllocationPolicy):
    """Keeps one run per outstanding delegation in reserve, and says what a delegation without a budget gets and what comes back with a result."""

    def __init__(self, budget: BudgetQuery, tasks: TaskQuery, mail: MailboxReader, settings: OrgSettings) -> None:
        self._budget = budget
        self._tasks = tasks
        self._mail = mail
        self._settings = settings

    def check_allocation(self, actor: str, amount: int, new_delegation: bool) -> None:
        if actor == ROOT or amount == 0:
            return
        remaining = self._budget.budget(actor) or 0
        reserve = len(self._tasks.outstanding(actor)) + (1 if new_delegation else 0)
        if remaining - amount < reserve:
            raise OrgError(
                f"not enough budget: you have {remaining} run(s) and must keep {reserve} in reserve "
                f"(one per outstanding delegation, to process its result), so you can hand down at most "
                f"{max(0, remaining - reserve)}. Ask your parent for more budget or do less."
            )

    def default_budget(self, actor: str) -> int:
        default = int(cast("SupportsInt | str", self._settings.config()["default_budget"]))
        if actor == ROOT:
            return default
        remaining = self._budget.budget(actor) or 0
        reserve = len(self._tasks.outstanding(actor)) + 1
        affordable = remaining - reserve
        if affordable < 1:
            raise OrgError(
                f"you cannot afford this delegation: you have {remaining} run(s) and must keep {reserve} in reserve "
                "(one per outstanding delegation, plus one to process the result of this one), so nothing is left "
                "to hand down. Options: ask your parent for more budget with `send` and end your run; do the work "
                "yourself; or, if the task cannot be completed without this step, report `blocked` (never `done`) "
                "and say what is missing."
            )
        return min(default, affordable)

    def budget_to_return(self, actor: str, task: Message, status: str) -> int:
        if status == "blocked" or task.sender != parent(actor):
            return 0
        busy = (
            [t for t in self._tasks.open_tasks(actor) if t.id != task.id]
            or self._blocked_not_moved_past(actor, task)
            or self._tasks.outstanding(actor)
            or self._mail.unread(actor)
        )
        return 0 if busy else max(0, self._budget.budget(actor) or 0)

    def _blocked_not_moved_past(self, actor: str, task: Message) -> list[Message]:
        """The other tasks ``actor`` reported ``blocked`` that their assigner has not moved past (read only when this branch is reached)."""
        blocked = [t for t in self._tasks.blocked_tasks(actor) if t.id != task.id]
        if not blocked:
            return []
        latest = latest_results(self._mail.sent(actor))
        received = self._mail.received(actor)
        return [t for t in blocked if t.id not in latest or not moved_past(t, latest[t.id], received)]
