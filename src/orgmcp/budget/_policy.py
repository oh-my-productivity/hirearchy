"""The reserve rule of every hand-down of runs. Skeleton: RED."""

from __future__ import annotations

from ..kernel import Message
from ..mail import MailboxReader, TaskQuery
from ..settings import OrgSettings
from .api import AllocationPolicy, BudgetQuery


class ReserveAllocationPolicy(AllocationPolicy):
    """Keeps one run per outstanding delegation in reserve."""

    def __init__(self, budget: BudgetQuery, tasks: TaskQuery, mail: MailboxReader, settings: OrgSettings) -> None:
        self._budget = budget
        self._tasks = tasks
        self._mail = mail
        self._settings = settings

    def check_allocation(self, actor: str, amount: int, new_delegation: bool) -> None:
        raise NotImplementedError

    def default_budget(self, actor: str) -> int:
        raise NotImplementedError

    def budget_to_return(self, actor: str, task: Message, status: str) -> int:
        raise NotImplementedError
