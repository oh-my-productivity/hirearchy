"""The service fields a rework task inherits from the request it sends back."""

from __future__ import annotations

from collections.abc import Mapping

from ..agents import AgentDirectory
from ..dispatch import ReworkContext
from ..mail import MailboxReader
from .api import ServiceCatalog


class ServiceReworkContext(ReworkContext):
    """``service`` and ``contract`` are copied from the revised request; ``playbook`` is the version current now."""

    def __init__(self, mail: MailboxReader, agents: AgentDirectory, catalog: ServiceCatalog) -> None:
        self._mail = mail
        self._agents = agents
        self._catalog = catalog

    def fields_for(self, actor: str, revises: str) -> Mapping[str, object]:
        raise NotImplementedError
