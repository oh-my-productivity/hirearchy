"""The commands of the services, in one place: each is done by the part that owns its rule."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..kernel import Message
from ._protocols import ClientFeedback, ContractDefinitions, PlaybookAcknowledgements, PlaybookRevisions, ServiceRequests, ServiceRetirement
from .api import PlaybookChange, ServiceCommands


class RuleServiceCommands(ServiceCommands):
    """Defining, retiring, requesting, revising, rating and acknowledging are separate rules; this is the one surface that offers them together."""

    def __init__(
        self, definitions: ContractDefinitions, retirement: ServiceRetirement, revisions: PlaybookRevisions, requests: ServiceRequests,
        ratings: ClientFeedback, acknowledgements: PlaybookAcknowledgements,
    ) -> None:
        self._definitions = definitions
        self._retirement = retirement
        self._revisions = revisions
        self._requests = requests
        self._ratings = ratings
        self._acknowledgements = acknowledgements

    def define_service(
        self, actor: str, owner: str, name: str, *, description: str | None = None, inputs: object = None, acceptance: object = None,
        deliverable: Mapping[str, object] | None = None, budget: int | None = None, playbook: str | None = None, locked: bool | None = None,
        notes: str | None = None, add_acceptance: object = None, remove_acceptance: object = None, answers: str | None = None,
        about: str | None = None, words: str | None = None, sources: Sequence[Mapping[str, object]] | None = None, elicitation: str | None = None,
        approved_in: str | None = None,
    ) -> str:
        return self._definitions.define_service(
            actor, owner, name, description=description, inputs=inputs, acceptance=acceptance, deliverable=deliverable, budget=budget,
            playbook=playbook, locked=locked, notes=notes, add_acceptance=add_acceptance, remove_acceptance=remove_acceptance,
            answers=answers, about=about, words=words, sources=sources, elicitation=elicitation,
            approved_in=approved_in,
        )

    def retire_service(self, actor: str, owner: str, name: str, reason: str, approved_in: str = "") -> str:
        return self._retirement.retire_service(actor, owner, name, reason, approved_in)

    def request(
        self, actor: str, service: str, inputs: Mapping[str, object] | None, *, title: str = "", note: str = "",
        extra_acceptance: Sequence[str] | None = None, budget: int | None = None, revises: str | None = None,
        source: str | None = None, base: str | None = None,
    ) -> Message:
        return self._requests.request(
            actor, service, inputs, title=title, note=note, extra_acceptance=extra_acceptance, budget=budget, revises=revises, source=source,
            base=base,
        )

    def revise_playbook(
        self, actor: str, service: str, op: str | None, reason: str, evidence: Sequence[str], *, item: str | None = None, kind: str | None = None,
        text: str | None = None, when: str | None = None, then: str | None = None, after: str | None = None, version: int | None = None,
        acknowledged: str | None = None, content: str | None = None,
    ) -> PlaybookChange:
        return self._revisions.revise_playbook(
            actor, service, op, reason, evidence, item=item, kind=kind, text=text, when=when, then=then, after=after, version=version,
            acknowledged=acknowledged, content=content,
        )

    def feedback(
        self, actor: str, task_id: str, verdict: str, note: str = "", *, source: str | None = None, criterion: Sequence[str] | None = None,
        confirms: str | None = None,
    ) -> Message:
        return self._ratings.feedback(actor, task_id, verdict, note, source=source, criterion=criterion, confirms=confirms)

    def acknowledge_playbook(
        self, actor: str, owner: str, service: str, item: str, op: str, *, text_hash: str | None = None, words: str | None = None,
    ) -> Message:
        return self._acknowledgements.acknowledge_playbook(actor, owner, service, item, op, text_hash=text_hash, words=words)
