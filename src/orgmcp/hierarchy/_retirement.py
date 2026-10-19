"""Removing a direct report and its team (moved from ``Org.retire`` and ``Org.retire_team``)."""

from __future__ import annotations

from ..agents import AgentDirectory, AgentRegistry
from ..budget import BudgetQuery
from ..delivery import MessageDelivery
from ..kernel import Clock, EventSink
from ..mail import TaskQuery
from ..templates import Notices
from .api import Retired, Retirement


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
        raise NotImplementedError("B-hierarchy")

    def retire_team(self, actor: str, name: str, reason: str) -> Retired:
        raise NotImplementedError("B-hierarchy")
