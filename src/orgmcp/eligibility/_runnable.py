"""``DerivedRunnableQuery``: which agents may be started, from their mail, budget and pause flag."""

from __future__ import annotations

from collections.abc import Collection

from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..mail import MailboxReader
from .api import PauseStore, RunnableQuery


class DerivedRunnableQuery(RunnableQuery):
    def __init__(self, agents: AgentDirectory, mail: MailboxReader, pauses: PauseStore, budgets: BudgetQuery) -> None:
        self._agents = agents
        self._mail = mail
        self._pauses = pauses
        self._budgets = budgets

    def runnable(self, exclude: Collection[str] = ()) -> list[str]:
        out = []
        for a in self._agents.agents():
            if a in exclude or not self._mail.unread(a):
                continue
            reason = self._pauses.paused(a)
            if reason == "budget" and (self._budgets.budget(a) or 0) > 0:
                reason = None
            if not reason and (self._budgets.budget(a) or 0) > 0:
                out.append(a)
        return out

    def startable(self, addr: str) -> bool:
        if not self._mail.unread(addr) or (self._budgets.budget(addr) or 0) <= 0:
            return False
        return self._pauses.paused(addr) in (None, "budget")
