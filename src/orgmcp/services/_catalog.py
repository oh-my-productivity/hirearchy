"""Reads the contracts and the playbooks of the services."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..kernel import ROOT, norm
from ._parse import contract_of, playbook_of
from ._protocols import ServicePlaces
from .api import Contract, Playbook, ServiceCatalog, ServiceStore


class ContractServiceCatalog(ServiceCatalog):
    """The contract and the playbook are read from the store; the services of the direct reports are the ones a client can request."""

    def __init__(self, store: ServiceStore, agents: AgentDirectory, places: ServicePlaces) -> None:
        self._store = store
        self._agents = agents
        self._places = places

    def service_names(self, addr: str) -> list[str]:
        raise NotImplementedError

    def read_contract(self, owner: str, name: str) -> Contract | None:
        raise NotImplementedError

    def read_playbook(self, owner: str, name: str) -> Playbook:
        raise NotImplementedError

    def owned_services(self, owner: str) -> list[Contract]:
        raise NotImplementedError

    def requestable_services(self, actor: str) -> list[Contract]:
        raise NotImplementedError
