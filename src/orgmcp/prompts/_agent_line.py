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
        raise NotImplementedError("red: C-prompts")
