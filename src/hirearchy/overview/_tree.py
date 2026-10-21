"""``TextOrgTree``: the organization tree of ``status``."""

from __future__ import annotations

from ..agents import AgentDirectory, CharterReader
from ..budget import BudgetQuery
from ..eligibility import AgentStates
from ..kernel import ROOT, depth
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
        lines = [f"root (human): unread {self._mail.unread(ROOT)}, delegated {len(self._tasks.outstanding(ROOT))}"]
        for a in self._agents.agents():
            meta, _ = self._charters.charter(a)
            name = a.rsplit("/", 1)[-1]
            offered = self._services.service_names(a)
            lines.append(
                "  " * depth(a) + f"{name} [{meta.get('role', '?')}] {self._states.state(a)}  budget={self._budgets.budget(a)} "
                f"open={len(self._tasks.open_tasks(a))} delegated={len(self._tasks.outstanding(a))} unread={self._mail.unread(a)}"
                + (f" services: {', '.join(offered)}" if offered else "")
            )
        return "\n".join(lines)
