"""Budget derived from the mailboxes and the run logs (moved from ``Org.budget``, ``Org.delegable`` and ``Org.grant_hint``)."""

from __future__ import annotations

from ..agents import AgentDirectory, CharterReader
from ..kernel import ROOT, norm
from ..mail import MailboxReader, TaskQuery
from ._hint import grant_hint_text, most_delegable
from ._ports import RunCounter
from .api import BudgetQuery


class DerivedBudgetQuery(BudgetQuery):
    """Received minus handed down minus runs used: nothing is stored."""

    def __init__(self, mail: MailboxReader, runs: RunCounter, agents: AgentDirectory, charters: CharterReader, tasks: TaskQuery) -> None:
        self._mail = mail
        self._runs = runs
        self._agents = agents
        self._charters = charters
        self._tasks = tasks

    def budget(self, addr: str) -> int | None:
        a = norm(addr)
        if a == ROOT:
            return None
        got = sum(m.budget for m in self._mail.received(a))
        given = sum(m.budget for m in self._mail.sent(a))
        return got - given - self._runs.count(a)

    def delegable(self, addr: str) -> tuple[int, int, int]:
        budget = self.budget(addr) or 0
        out = len(self._tasks.outstanding(addr))
        return budget, out, most_delegable(budget, out)

    def grant_hint(self, addr: str) -> str:
        if not self._agents.exists(addr) or not self._charters.charter(addr)[0].get("can_hire"):
            return ""
        budget, out, _ = self.delegable(addr)
        return grant_hint_text(addr, budget, out)
