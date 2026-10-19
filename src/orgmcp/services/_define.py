"""The client defines a service for a direct report, or amends its contract."""

from __future__ import annotations

from collections.abc import Mapping

from ..agents import AgentDirectory
from ..delivery import MessageDelivery
from ..kernel import NAME_RE, ROOT, Clock, EventSink, JsonObject, OrgError, parent
from ._lines import criteria_lines
from ._protocols import ContractAmendment, ContractDefinitions, OwnerAddresses, PlaybookTexts, PlaybookWriter, ServicePlaces
from .api import DESCRIPTION_MAX, Contract, ContractNormalizer, ServiceCatalog, ServiceStore


class RuleContractDefiner(ContractDefinitions):
    """Only the parent of the owner defines or amends; a first definition is complete, an amendment keeps what it does not name."""

    def __init__(
        self, agents: AgentDirectory, catalog: ServiceCatalog, store: ServiceStore, places: ServicePlaces, normalizer: ContractNormalizer,
        amendment: ContractAmendment, texts: PlaybookTexts, owners: OwnerAddresses, playbooks: PlaybookWriter, delivery: MessageDelivery,
        clock: Clock, events: EventSink,
    ) -> None:
        self._agents = agents
        self._catalog = catalog
        self._store = store
        self._places = places
        self._normalizer = normalizer
        self._amendment = amendment
        self._texts = texts
        self._owners = owners
        self._playbooks = playbooks
        self._delivery = delivery
        self._clock = clock
        self._events = events

    def define_service(
        self, actor: str, owner: str, name: str, *, description: str | None, inputs: object, acceptance: object,
        deliverable: Mapping[str, object] | None, budget: int | None, playbook: str | None, locked: bool | None, notes: str | None,
        add_acceptance: object, remove_acceptance: object,
    ) -> str:
        raise NotImplementedError
