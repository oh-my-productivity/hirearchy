"""The team of a root task (moved from ``progress._task_line`` and ``_snapshot``)."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..kernel import Message
from ._ports import TaskTeams


class AgentTaskTeams(TaskTeams):
    def __init__(self, agents: AgentDirectory) -> None:
        self._agents = agents

    def team_of(self, task: Message) -> list[str]:
        raise NotImplementedError("red: C-progress")
