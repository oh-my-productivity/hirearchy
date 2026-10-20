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
        actor = self._agents.require(actor)
        contract = self._owned(actor, service)
        client = parent(actor) or ROOT
        if contract.locked:
            raise OrgError(
                f"the contract of `{service}` is locked by {client}: you may not revise its playbook. Follow the current "
                f"one, and if you think it must change, tell {client} (`send`)."
            )
        reason = (reason or "").strip()
        if not reason or len(reason) > REASON_MAX:
            raise OrgError(
                f"reason is 1-{REASON_MAX} characters: say what changed and which cases it rests on (case ids from the "
                "evidence), so the next revision can judge it"
            )
        body = self._texts.body(content)
        current = self._catalog.read_playbook(actor, service)
        if current.version and body == current.body.strip():
            raise OrgError(
                f"no change: this is identical to playbook v{current.version}. Revise only when the evidence calls for a "
                "different way of working."
            )
        version = current.version + 1
        path = self._playbooks.write(actor, service, version, body, actor, reason, current.version or None)
        self._delivery.notify(
            client, f"playbook of {service} revised to v{version}",
            f"{actor} revised the playbook of service `{service}` to v{version}.\nReason: {reason}\nFile: {path}",
            wake=False,
        )
        return version

    def _owned(self, actor: str, name: str) -> Contract:
        """The contract of ``name`` among the services ``actor`` owns, or an error listing the ones it owns."""
        contract = self._catalog.read_contract(actor, name) if NAME_RE.fullmatch(name or "") else None
        if contract is None:
            mine = ", ".join(self._catalog.service_names(actor)) or "none"
            raise OrgError(
                f"you do not own a service called `{name}`. Services you own: {mine}. Only the owner revises a "
                "playbook, and services are defined for you by your parent (define_service)."
            )
        return contract
