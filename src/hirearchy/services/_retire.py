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
        actor = self._agents.require(actor)
        owner = self._owners.resolve(actor, owner)
        if owner == ROOT or not self._agents.exists(owner) or parent(owner) != actor:
            raise OrgError(f"you can only retire services of your direct reports (root: top-level agents); {owner!r} is not one")
        if self._catalog.read_contract(owner, name) is None:
            known = ", ".join(self._catalog.service_names(owner)) or "none"
            raise OrgError(f"{owner} offers no service called `{name}`. Its services: {known}")
        if not (reason or "").strip():
            raise OrgError("say why the service is retired (reason)")
        dest = self._store.retire(owner, name, f"{self._clock.now():%Y%m%dT%H%M%S%f}")
        self._events.emit("service.retire", actor=actor, owner=owner, service=name, by=actor)
        self._delivery.notify(
            owner, f"service {name} retired",
            f"{actor} retired the service `{name}`: {reason.strip()}. It cannot be requested any more; its files are kept at "
            f"{dest}.", wake=False,
        )
        return f"retired service `{name}` of {owner}; files kept at {dest}"
