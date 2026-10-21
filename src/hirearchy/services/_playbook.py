"""The owner of a service revises its playbook."""

from __future__ import annotations

from collections.abc import Sequence

from ..agents import AgentDirectory
from ..delivery import MessageDelivery
from ..kernel import NAME_RE, ROOT, OrgError, parent
from ._protocols import PlaybookRevisions, PlaybookTexts, PlaybookWriter
from .api import REASON_MAX, Admission, Contract, ServiceCatalog, ServiceEvidence, normalize_evidence


class RulePlaybookReviser(PlaybookRevisions):
    """Only the owner, only while the contract is not locked, only with a reason, evidence the gate admits and a different text; the client is
    told quietly. The first version and the restoring of a version the client wrote need no evidence (the gate is asked to resolve the ids only)."""

    def __init__(
        self, agents: AgentDirectory, catalog: ServiceCatalog, texts: PlaybookTexts, playbooks: PlaybookWriter, delivery: MessageDelivery,
        evidence: ServiceEvidence,
    ) -> None:
        self._agents = agents
        self._catalog = catalog
        self._texts = texts
        self._playbooks = playbooks
        self._delivery = delivery
        self._evidence = evidence

    def revise_playbook(self, actor: str, service: str, content: str, reason: str, evidence: Sequence[str]) -> int:
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
        ids = normalize_evidence(evidence)
        body = self._texts.body(content)
        versions = self._catalog.playbook_versions(actor, service)
        current = self._catalog.read_playbook(actor, service)
        if current.version and body == current.body.strip():
            raise OrgError(
                f"no change: this is identical to playbook v{current.version}. Revise only when the evidence calls for a "
                "different way of working."
            )
        exempt, restores = None, None
        if not current.version:
            exempt = "first"
        else:
            same = [p for p in versions if p.version < current.version and p.body.strip() == body]
            if same:
                restored = max(same, key=lambda p: p.version)
                restores = restored.version
                exempt = "restore" if restored.by == client else None
        admission = self._evidence.admit(actor, service, ids, reason, exempt=exempt)
        version = current.version + 1
        extra: dict[str, object] = {"evidence": list(admission.evidence), "admitted": admission.rule}
        if restores:
            extra["restores"] = restores
        path = self._playbooks.write(actor, service, version, body, actor, reason, current.version or None, extra)
        self._delivery.notify(
            client, f"playbook of {service} revised to v{version}",
            f"{actor} revised the playbook of service `{service}` to v{version}.\nReason: {reason}\n"
            f"Evidence: {', '.join(admission.evidence) or 'none'}; {self._admission(admission, restores)}\nFile: {path}",
            wake=False,
        )
        return version

    @staticmethod
    def _admission(admission: Admission, restores: int | None) -> str:
        """How the client's note says the revision was admitted."""
        if admission.rule == "first":
            return "the first playbook (no evidence needed)"
        if admission.rule == "restore":
            return f"restores v{restores}, which you wrote (no evidence needed)"
        return f"restores v{restores}; admitted: {admission.detail}" if restores else f"admitted: {admission.detail}"

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
