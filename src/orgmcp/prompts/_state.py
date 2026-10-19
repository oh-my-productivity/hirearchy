"""``TextStateSummarizer``: the situation of an agent (moved from ``Org.state_summary``)."""

from __future__ import annotations

from collections.abc import Collection

from ..agents import AgentDirectory, CharterReader
from ..budget import BudgetQuery
from ._ports import AgentLines, DelegationLines, FilesLines, HeldTaskLines
from .api import StateSummarizer


class TextStateSummarizer(StateSummarizer):
    def __init__(
        self, agents: AgentDirectory, charters: CharterReader, budgets: BudgetQuery, files: FilesLines, agent_lines: AgentLines,
        held: HeldTaskLines, delegations: DelegationLines,
    ) -> None:
        self._agents = agents
        self._charters = charters
        self._budgets = budgets
        self._files = files
        self._agent_lines = agent_lines
        self._held = held
        self._delegations = delegations

    def state_summary(self, addr: str, shown: Collection[str] | None = None) -> str:
        raise NotImplementedError("red: C-prompts")
