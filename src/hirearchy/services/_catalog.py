"""Reads the contracts and the playbooks of the services."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..kernel import ROOT, norm
from ._criteria import stored_versions
from ._parse import contract_of, playbook_of
from ._protocols import ServicePlaces
from .api import Contract, Criterion, Playbook, ServiceCatalog, ServiceStore, number_criteria


class ContractServiceCatalog(ServiceCatalog):
    """The contract and the playbook are read from the store; the services of the direct reports are the ones a client can request."""

    def __init__(self, store: ServiceStore, agents: AgentDirectory, places: ServicePlaces) -> None:
        self._store = store
        self._agents = agents
        self._places = places

    def service_names(self, addr: str) -> list[str]:
        a = norm(addr)
        return [] if a == ROOT else self._store.names(a)

    def read_contract(self, owner: str, name: str) -> Contract | None:
        found = self._store.read_contract(owner, name)
        if found is None:
            return None
        meta, body = found
        return contract_of(owner, name, meta, body, self._places.contract_file(owner, name))

    def read_playbook(self, owner: str, name: str) -> Playbook:
        found = self._store.read_playbook(owner, name)
        if found is None:
            return Playbook()
        meta, body = found
        return playbook_of(meta, body, self._places.playbook_file(owner, name))

    def owned_services(self, owner: str) -> list[Contract]:
        return [c for n in self.service_names(owner) if (c := self.read_contract(owner, n)) is not None]

    def requestable_services(self, actor: str) -> list[Contract]:
        return [c for kid in self._agents.children(actor) for c in self.owned_services(kid)]

    def criteria(self, owner: str, name: str) -> list[Criterion]:
        return number_criteria(stored_versions(self._store, owner, name))

    def playbook_versions(self, owner: str, name: str) -> list[Playbook]:
        return [playbook_of(meta, body, None) for _, meta, body in self._store.versions(owner, name, "PLAYBOOK")]
