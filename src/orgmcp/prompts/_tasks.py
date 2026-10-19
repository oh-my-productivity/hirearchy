"""The task blocks of a state summary: the tasks held (open or reported blocked) and the delegations outstanding (moved from ``Org.state_summary``)."""

from __future__ import annotations

from collections.abc import Collection

from ..agents import AgentDirectory
from ..eligibility import AgentStates
from ..mail import TaskQuery
from ._ports import DelegationLines, HeldTaskLines, TaskQuoter
from ._text import indent


class HeldTasks(HeldTaskLines):
    def __init__(self, tasks: TaskQuery, quoter: TaskQuoter) -> None:
        self._tasks = tasks
        self._quoter = quoter

    def lines(self, addr: str, shown: Collection[str]) -> list[str]:
        lines = []
        tasks = self._tasks.open_tasks(addr)
        lines.append("- Open tasks assigned to you:" + ("" if tasks else " none"))
        for t in tasks:
            lines.append(f"  - {t.id} \"{t.title}\" from {t.sender}")
            if t.id in shown:
                lines.append("    (full text: see the new messages below)")
            else:  # the contract you are accountable for, verbatim
                lines.append(indent(self._quoter.quote(t), 4))
        blocked = self._tasks.blocked_tasks(addr)
        if blocked:
            lines.append("- Tasks you reported blocked (not final):")
            for t in blocked:
                lines.append(
                    f"  - {t.id} \"{t.title}\" from {t.sender}: reported blocked; "
                    "you may re-report it once the blocker is resolved"
                )
                if t.id in shown:
                    lines.append("    (full text: see the new messages below)")
                else:
                    lines.append(indent(self._quoter.quote(t), 4))
        return lines


class OutstandingDelegations(DelegationLines):
    def __init__(self, tasks: TaskQuery, agents: AgentDirectory, states: AgentStates) -> None:
        self._tasks = tasks
        self._agents = agents
        self._states = states

    def lines(self, addr: str) -> list[str]:
        out = self._tasks.outstanding(addr)
        lines = ["- Work you delegated that is still outstanding:" + ("" if out else " none")]
        lines += [
            f"  - {t.id} \"{t.title}\" -> {t.to} ({self._states.state(t.to) if self._agents.exists(t.to) else 'gone'})" for t in out
        ]
        return lines
