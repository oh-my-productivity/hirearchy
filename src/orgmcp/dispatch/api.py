"""The public surface of ``dispatch``: the protocol rules every message an agent or the human sends obeys.

``MessageSender`` validates (size, type, body, route, budget, hops) and delivers, ``TaskAssigner`` is how a manager gives a task to a direct
report, ``TaskReporter`` is how an agent answers a task it was given. ``ReworkContext`` is the port that ``services`` implements: the service
fields a rework task inherits from the task it revises.

The rules the three of them are made of are ports too, since the facade (``Org.can_message``, ``_next_hops``, ``_normalize_artifact``) and the
runtime hand them out: ``RoutePolicy`` (who may message whom), ``HopCounter`` (the ``hops`` of the next message) and ``ArtifactNormalizer`` (an artifact
of a report, checked and annotated). ``check_lessons`` is the lessons rule as a function (``Org._check_lessons`` is static).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from ..kernel import Message
from ._lessons import LESSONS_MAX_CHARS, check_lessons
from ._protocols import ArtifactNormalizer, HopCounter, RoutePolicy

__all__ = [
    "LESSONS_MAX_CHARS",
    "ArtifactNormalizer",
    "HopCounter",
    "MessageSender",
    "ReworkContext",
    "RoutePolicy",
    "TaskAssigner",
    "TaskReporter",
    "check_lessons",
]


@runtime_checkable
class MessageSender(Protocol):
    def send(
        self,
        actor: str,
        to: str,
        body: str,
        *,
        type: str = "note",
        title: str = "",
        reply_to: str | None = None,
        status: str | None = None,
        budget: int = 0,
        revises: str | None = None,
        supersedes: str | None = None,
        service: str | None = None,
        contract: int | None = None,
        playbook: int | None = None,
        feedback: str | None = None,
        wake: bool = True,
        skip_route_check: bool = False,
    ) -> Message:
        """Check the message against the protocol, deliver it and return the delivered message. The checks, in this order: the size of the body
        (``max_message_chars``, not for root: the human may paste), both addresses exist, the type, an empty body, the route (``actor`` may
        message its parent, its direct reports, its siblings, and whoever sent the message it replies to; the human and the runtime may message
        anyone; ``skip_route_check`` skips it, for results), a negative budget, budget only to a direct report or back to the parent, the
        reserve every hand-down keeps, and the hop limit (``max_hops``; results always get through). Every refusal is an ``OrgError`` whose
        text agents are shown. The body and the title are stripped; ``hops`` is one more than the longest chain the actor is working on."""
        ...


@runtime_checkable
class TaskAssigner(Protocol):
    def delegate(
        self,
        actor: str,
        to: str,
        title: str,
        goal: str,
        acceptance: str,
        inputs: Sequence[str] | None = None,
        budget: int | None = None,
        revises: str | None = None,
    ) -> Message:
        """Assign a task to a direct report (root: to anyone) and return the delivered task. A title, a goal and acceptance criteria are
        required; ``budget`` defaults to what ``actor`` can afford (at least 1 run); ``revises`` must be the id of an earlier task ``actor``
        sent to ``to`` and sends it back for rework, and a rework of a service request keeps the service fields of the original."""
        ...


@runtime_checkable
class TaskReporter(Protocol):
    def report(
        self,
        actor: str,
        task_id: str,
        status: str,
        summary: str,
        artifacts: Sequence[str] | None = None,
        lessons: str | None = None,
    ) -> Message:
        """Answer a task assigned to ``actor`` and return the delivered result, which goes to whoever assigned it. ``done`` and ``failed``
        are final; ``blocked`` can be reported again (the new result supersedes the old one). Every artifact must exist inside the
        organization or, by absolute path, inside the reporter's own workspace; it is shown with its word count and whether it changed since
        the task was assigned. ``lessons`` (1 to ``LESSONS_MAX_CHARS`` characters) are required on a request for a service. A final result
        carries back the budget the reporter has left when nothing else needs it."""
        ...


@runtime_checkable
class ReworkContext(Protocol):
    def fields_for(self, actor: str, revises: str) -> Mapping[str, object]:
        """The service fields a rework task inherits from the task ``actor`` sent with id ``revises``: ``service`` and ``contract`` of that
        task and the ``playbook`` version current now. Empty for an ordinary task (or one that is not found)."""
        ...
