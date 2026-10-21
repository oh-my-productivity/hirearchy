"""``StatusAgentLine``: the one line that says where an agent stands (moved from ``Org._agent_line``)."""

from __future__ import annotations

from ..agents import CharterReader
from ..budget import BudgetQuery
from ..eligibility import AgentStates
from ..mail import MailboxReader, TaskQuery
from ._ports import AgentLines


class StatusAgentLine(AgentLines):
    def __init__(self, charters: CharterReader, states: AgentStates, budgets: BudgetQuery, tasks: TaskQuery, mail: MailboxReader) -> None:
        self._charters = charters
        self._states = states
        self._budgets = budgets
        self._tasks = tasks
        self._mail = mail

    def agent_line(self, addr: str) -> str:
        meta, _ = self._charters.charter(addr)
        return (
            f"{addr} [{meta.get('role', '?')}] {self._states.state(addr)}, budget {self._budgets.budget(addr)}, "
            f"open tasks {len(self._tasks.open_tasks(addr))}, delegated {len(self._tasks.outstanding(addr))}, unread {self._mail.unread(addr)}"
        )
