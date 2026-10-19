"""The team of a root task (moved from ``progress._task_line`` and ``_snapshot``)."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..kernel import ROOT, Message
from ._ports import TaskTeams


class AgentTaskTeams(TaskTeams):
    def __init__(self, agents: AgentDirectory) -> None:
        self._agents = agents

    def team_of(self, task: Message) -> list[str]:
        return [a for a in self._agents.subtree(task.to) if a != ROOT] if self._agents.exists(task.to) else []
