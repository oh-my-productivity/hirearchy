"""The owner of a service revises its playbook."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..delivery import MessageDelivery
from ..kernel import NAME_RE, ROOT, OrgError, parent
from ._protocols import PlaybookRevisions, PlaybookTexts, PlaybookWriter
from .api import REASON_MAX, Contract, ServiceCatalog


class RulePlaybookReviser(PlaybookRevisions):
    """Only the owner, only while the contract is not locked, only with a reason and a different text; the client is told quietly."""

    def __init__(
        self, agents: AgentDirectory, catalog: ServiceCatalog, texts: PlaybookTexts, playbooks: PlaybookWriter, delivery: MessageDelivery,
    ) -> None:
        self._agents = agents
        self._catalog = catalog
        self._texts = texts
        self._playbooks = playbooks
        self._delivery = delivery

    def revise_playbook(self, actor: str, service: str, content: str, reason: str) -> int:
        raise NotImplementedError

    def _owned(self, actor: str, name: str) -> Contract:
        """The contract of ``name`` among the services ``actor`` owns, or an error listing the ones it owns."""
        raise NotImplementedError
