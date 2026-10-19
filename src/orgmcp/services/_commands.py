"""The commands of the services, in one place: each is done by the part that owns its rule."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..kernel import Message
from ._protocols import ClientFeedback, ContractDefinitions, PlaybookRevisions, ServiceRequests, ServiceRetirement
from .api import ServiceCommands


class RuleServiceCommands(ServiceCommands):
    """Defining, retiring, requesting, revising and rating are separate rules; this is the one surface that offers them together."""

    def __init__(
        self, definitions: ContractDefinitions, retirement: ServiceRetirement, revisions: PlaybookRevisions, requests: ServiceRequests,
        ratings: ClientFeedback,
    ) -> None:
        self._definitions = definitions
        self._retirement = retirement
        self._revisions = revisions
        self._requests = requests
        self._ratings = ratings

    def define_service(
        self, actor: str, owner: str, name: str, *, description: str | None = None, inputs: object = None, acceptance: object = None,
        deliverable: Mapping[str, object] | None = None, budget: int | None = None, playbook: str | None = None, locked: bool | None = None,
        notes: str | None = None, add_acceptance: object = None, remove_acceptance: object = None,
    ) -> str:
        raise NotImplementedError

    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        raise NotImplementedError

    def request(
        self, actor: str, service: str, inputs: Mapping[str, object] | None, *, title: str = "", note: str = "",
        extra_acceptance: Sequence[str] | None = None, budget: int | None = None, revises: str | None = None,
    ) -> Message:
        raise NotImplementedError

    def revise_playbook(self, actor: str, service: str, content: str, reason: str) -> int:
        raise NotImplementedError

    def feedback(self, actor: str, task_id: str, verdict: str, note: str = "") -> Message:
        raise NotImplementedError
