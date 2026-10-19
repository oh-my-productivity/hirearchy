"""Removing a direct report and its team (moved from ``Org.retire`` and ``Org.retire_team``)."""

from __future__ import annotations

from ..agents import AgentDirectory, AgentRegistry
from ..budget import BudgetQuery
from ..delivery import MessageDelivery
from ..kernel import ROOT, RUNTIME, Clock, EventSink, Message, OrgError, child_addr, clip, norm, parent
from ..mail import TaskQuery
from ..templates import Notices
from .api import Retired, Retirement

ERROR_MAX = 500  # the longest reason that goes into an event (the longest error text of an event: telemetry.ERROR_MAX)


class RuleRetirement(Retirement):
    """Fails what the team owes, archives it, and gives its unspent runs back to the parent."""

    def __init__(
        self,
        agents: AgentDirectory,
        registry: AgentRegistry,
        tasks: TaskQuery,
        budget: BudgetQuery,
        delivery: MessageDelivery,
        notices: Notices,
        clock: Clock,
        events: EventSink,
    ) -> None:
        self._agents = agents
        self._registry = registry
        self._tasks = tasks
        self._budget = budget
        self._delivery = delivery
        self._notices = notices
        self._clock = clock
        self._events = events

    def retire(self, actor: str, name: str, reason: str) -> str:
        """Remove a direct report and its team; returns the retired address. See :meth:`retire_team`."""
        return self.retire_team(actor, name, reason).addr

    def retire_team(self, actor: str, name: str, reason: str) -> Retired:
        """Retire a direct report (short name or full address; root: any agent by full address) and its team.

        Open tasks the team owes the outside are closed as failed, and the team's unspent budget is returned to the
        retired agent's parent as a non-waking runtime note carrying the budget (nothing when the parent is root, who has no
        limit), so budget stays derived from files and is neither destroyed nor minted.
        """
        actor = self._agents.require(actor)
        short = norm(name)
        addr = short if "/" in short else child_addr(actor, short)
        addr = self._agents.require(addr)
        if addr == ROOT:
            raise OrgError("the root of the organization cannot be retired")
        if actor != ROOT and parent(addr) != actor:
            raise OrgError("you can only retire your direct reports")
        team = set(self._agents.subtree(addr))
        for a in team:  # close every task the team owes to the outside world
            for task in self._tasks.open_tasks(a):
                if task.sender not in team and self._agents.exists(task.sender):
                    self._delivery.deliver(Message(
                        sender=a, to=task.sender, type="result", title=task.title, reply_to=task.id,
                        status="failed", body=f"## Summary\nAgent {a} was retired by {actor}: {reason}",
                    ))
        owner = parent(addr)
        # Grants inside the team cancel out, so this is what the parent handed down minus what the team ran.
        refund = max(0, sum(self._budget.budget(a) or 0 for a in team)) if owner != ROOT else 0
        self._registry.archive(addr, f"{self._clock.now():%Y%m%dT%H%M%S}")
        if refund:  # after the move: a crash in between loses the refund rather than counting it twice
            assert owner is not None  # a refund is only due to a parent that is not root
            self._delivery.deliver(Message(
                sender=RUNTIME, to=owner, type="note", budget=refund, wake=False, title=f"Budget returned from {addr}",
                body=self._notices.budget_returned(addr, refund, actor, reason),
            ))
        self._events.emit("agent.retire", actor=actor, agent=addr, by=actor, reason=clip(reason, ERROR_MAX),
                          returned_budget=refund, team=sorted(team))
        return Retired(addr, refund, owner if refund else None)
