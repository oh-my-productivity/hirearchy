"""Budget derived from the mailboxes and the run logs. Skeleton: RED."""

from __future__ import annotations

from ..agents import AgentDirectory, CharterReader
from ..mail import MailboxReader, TaskQuery
from ._ports import RunCounter
from .api import BudgetQuery


class DerivedBudgetQuery(BudgetQuery):
    """Received minus handed down minus runs used."""

    def __init__(self, mail: MailboxReader, runs: RunCounter, agents: AgentDirectory, charters: CharterReader, tasks: TaskQuery) -> None:
        self._mail = mail
        self._runs = runs
        self._agents = agents
        self._charters = charters
        self._tasks = tasks

    def budget(self, addr: str) -> int | None:
        raise NotImplementedError

    def delegable(self, addr: str) -> tuple[int, int, int]:
        raise NotImplementedError

    def grant_hint(self, addr: str) -> str:
        raise NotImplementedError
