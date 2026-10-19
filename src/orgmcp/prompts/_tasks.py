"""The task lines of a state summary: the tasks held (open or reported blocked) and the delegations outstanding (moved from ``Org.state_summary``)."""

from __future__ import annotations

from collections.abc import Collection

from ..agents import AgentDirectory
from ..eligibility import AgentStates
from ..mail import TaskQuery
from ._ports import DelegationLines, HeldTaskLines, TaskQuoter


class HeldTasks(HeldTaskLines):
    def __init__(self, tasks: TaskQuery, quoter: TaskQuoter) -> None:
        self._tasks = tasks
        self._quoter = quoter

    def lines(self, addr: str, shown: Collection[str]) -> list[str]:
        raise NotImplementedError("red: C-prompts")


class OutstandingDelegations(DelegationLines):
    def __init__(self, tasks: TaskQuery, agents: AgentDirectory, states: AgentStates) -> None:
        self._tasks = tasks
        self._agents = agents
        self._states = states

    def lines(self, addr: str) -> list[str]:
        raise NotImplementedError("red: C-prompts")
