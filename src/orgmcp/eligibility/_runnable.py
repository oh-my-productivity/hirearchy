"""``DerivedRunnableQuery``: which agents may be started, from their mail, budget and pause flag."""

from __future__ import annotations

from collections.abc import Collection

from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..mail import MailboxReader
from .api import PauseStore, RunnableQuery


class DerivedRunnableQuery(RunnableQuery):
    def __init__(self, agents: AgentDirectory, mail: MailboxReader, pauses: PauseStore, budgets: BudgetQuery) -> None:
        raise NotImplementedError("red: B-eligibility")

    def runnable(self, exclude: Collection[str] = ()) -> list[str]:
        raise NotImplementedError("red: B-eligibility")

    def startable(self, addr: str) -> bool:
        raise NotImplementedError("red: B-eligibility")
