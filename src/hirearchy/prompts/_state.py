"""``TextStateSummarizer``: the situation of an agent (moved from ``Org.state_summary``)."""

from __future__ import annotations

from collections.abc import Collection, Iterable
from typing import cast

from ..agents import AgentDirectory, CharterReader
from ..budget import BudgetQuery
from ..kernel import ROOT, parent
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
        """The agent's situation. ``shown``: ids of tasks whose full text the caller already prints elsewhere."""
        a = self._agents.require(addr)
        meta, _ = self._charters.charter(a)
        lines = [f"- Address: `{a}`; parent: `{parent(a) or '-'}`; role: {meta.get('role', '?')}"]
        if a != ROOT:
            hiring = (
                f"allowed ({len(self._agents.children(a))}/{meta.get('max_children', 5)} reports)"
                if meta.get("can_hire") else "not allowed"
            )
            tools = ", ".join(cast("Iterable[str]", meta.get("tools") or [])) or "none"
            lines.append(f"- Budget: {self._budgets.budget(a)} run(s) left (this run already counted). Hiring: {hiring}")
            lines.append(f"- Tools beyond hirearchy: {tools}" + (f"; workspace: {meta['workspace']}" if meta.get("workspace") else ""))
            lines += self._files.lines(a, meta)
        kids = self._agents.children(a)
        lines.append("- Direct reports:" + ("" if kids else " none"))
        lines += [f"  - {self._agent_lines.agent_line(k)}" for k in kids]
        siblings = [s for s in self._agents.children(parent(a) or ROOT) if s != a] if a != ROOT else []
        if siblings:
            lines.append("- Siblings: " + ", ".join(siblings))
        lines += self._held.lines(a, frozenset(shown or ()))
        lines += self._delegations.lines(a)
        return "\n".join(lines)
