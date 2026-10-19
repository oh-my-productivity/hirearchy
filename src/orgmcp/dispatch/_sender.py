"""The checks every message passes before it is delivered. Skeleton: RED."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..budget import AllocationPolicy
from ..delivery import MessageDelivery
from ..kernel import Message
from ..settings import OrgSettings
from ._protocols import HopCounter, RoutePolicy
from .api import MessageSender


class RuleMessageSender(MessageSender):
    """Size, type, body, route, budget and hops, in this order; then delivery."""

    def __init__(
        self, agents: AgentDirectory, settings: OrgSettings, routes: RoutePolicy, allocation: AllocationPolicy, hops: HopCounter,
        delivery: MessageDelivery,
    ) -> None:
        self._agents = agents
        self._settings = settings
        self._routes = routes
        self._allocation = allocation
        self._hops = hops
        self._delivery = delivery

    def send(
        self, actor: str, to: str, body: str, *, type: str = "note", title: str = "", reply_to: str | None = None,
        status: str | None = None, budget: int = 0, revises: str | None = None, supersedes: str | None = None,
        service: str | None = None, contract: int | None = None, playbook: int | None = None, feedback: str | None = None,
        wake: bool = True, skip_route_check: bool = False,
    ) -> Message:
        raise NotImplementedError
