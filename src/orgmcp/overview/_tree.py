"""``TextOrgTree``: the organization tree of ``status``."""

from __future__ import annotations

from ..agents import AgentDirectory, CharterReader
from ..budget import BudgetQuery
from ..eligibility import AgentStates
from ..mail import MailboxReader, TaskQuery
from ._ports import ServiceNames
from .api import OrgTree


class TextOrgTree(OrgTree):
    def __init__(
        self, agents: AgentDirectory, charters: CharterReader, mail: MailboxReader, tasks: TaskQuery, budgets: BudgetQuery,
        states: AgentStates, services: ServiceNames,
    ) -> None:
        self._agents = agents
        self._charters = charters
        self._mail = mail
        self._tasks = tasks
        self._budgets = budgets
        self._states = states
        self._services = services

    def tree(self) -> str:
        raise NotImplementedError("red: C-overview")
