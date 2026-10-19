"""Taking unspent runs back as a note. Skeleton: RED."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..delivery import MessageDelivery
from ..kernel import Message
from ..mail import MailboxReader, TaskQuery
from .api import BudgetQuery, BudgetReclaimer


class NoteBudgetReclaimer(BudgetReclaimer):
    """Writes, on an idle report's behalf, the note that moves its unspent runs to its manager."""

    def __init__(
        self, delivery: MessageDelivery, budget: BudgetQuery, tasks: TaskQuery, mail: MailboxReader, agents: AgentDirectory,
    ) -> None:
        self._delivery = delivery
        self._budget = budget
        self._tasks = tasks
        self._mail = mail
        self._agents = agents

    def reclaim(self, actor: str, report: str, budget: int | None = None) -> Message:
        raise NotImplementedError
