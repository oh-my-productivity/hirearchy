"""The client takes a service of a direct report out of use."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..delivery import MessageDelivery
from ..kernel import ROOT, Clock, EventSink, OrgError, parent
from ._protocols import OwnerAddresses, ServiceRetirement
from .api import ServiceCatalog, ServiceStore


class RuleServiceRetirement(ServiceRetirement):
    """Same authority as a definition: the parent of the owner. The files are kept, under ``services/.retired``."""

    def __init__(
        self, agents: AgentDirectory, catalog: ServiceCatalog, store: ServiceStore, owners: OwnerAddresses, delivery: MessageDelivery,
        clock: Clock, events: EventSink,
    ) -> None:
        self._agents = agents
        self._catalog = catalog
        self._store = store
        self._owners = owners
        self._delivery = delivery
        self._clock = clock
        self._events = events

    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        raise NotImplementedError
