"""The public surface of ``dispatch``: the protocol rules every message an agent or the human sends obeys.

``MessageSender`` validates (size, type, body, route, budget, hops) and delivers, ``TaskAssigner`` is how a manager gives a task to a direct
report, ``TaskReporter`` is how an agent answers a task it was given. ``GuardedSender`` is the sender behind ``Org.send``. ``ReworkContext`` is the port that ``services`` implements: the service
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
from ._root_send import check_root_send

__all__ = [
    "LESSONS_MAX_CHARS",
    "ArtifactNormalizer",
    "GuardedSender",
    "HopCounter",
    "MessageSender",
    "ReworkContext",
    "RoutePolicy",
    "TaskAssigner",
    "TaskReporter",
    "check_lessons",
    "check_root_send",
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
        source: str | None = None,
        criterion: str | None = None,
        wake: bool = True,
        skip_route_check: bool = False,
        inherited: str | None = None,
    ) -> Message:
        """Check the message against the protocol, deliver it and return the delivered message. The checks, in this order: the size of the body
        (``max_message_chars``, not for root: the human may paste), both addresses exist, the type, an empty body, the route (``actor`` may
        message its parent, its direct reports, its siblings, and whoever sent the message it replies to; the human and the runtime may message
        anyone; ``skip_route_check`` skips it, for results), a negative budget, budget only to a direct report or back to the parent, the
        reserve every hand-down keeps, and the hop limit (``max_hops``; results always get through). Every refusal is an ``OrgError`` whose
        text agents are shown. The body and the title are stripped; ``hops`` is one more than the longest chain the actor is working on.

        Provenance: only root records where a message comes from (``source``, ``"human"`` or ``"relayed"``) and what a verdict is about
        (``criterion``, ids joined by ``", "``): an agent that passes either, or a ``source`` that is neither value, is refused. ``criterion``
        goes only on a verdict note (a note with ``feedback``) or on a link note (a note without ``feedback`` that replies to one). A task from
        root that ``revises`` another (a rework), a verdict note and a link note without a ``source`` are stamped ``"relayed"`` (root's own
        reading); a fresh task of root, any other note and every message of an agent stay unstamped unless root says. A task of an
        agent carries the tier its sender works under (``inherited``, from ``ReworkContext``): the runtime's copy, never the agent's declaration."""
        ...


@runtime_checkable
class GuardedSender(MessageSender, Protocol):
    """The ``MessageSender`` the ``Org`` facade hands out for ``Org.send``: it refuses what only the rules of a case may send for root (``check_root_send``:
    a task that names a service or revises another) and sends every other message exactly as the sender it guards would."""


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
        source: str | None = None,
    ) -> Message:
        """Assign a task to a direct report (root: to anyone) and return the delivered task. A title, a goal and acceptance criteria are
        required; ``budget`` defaults to what ``actor`` can afford (at least 1 run); ``revises`` must be the id of an earlier task ``actor``
        sent to ``to`` and sends it back for rework, and an agent's rework of a service request keeps the service fields of the original (root sends a service
        request back with ``ServiceCommands.request``: ``delegate`` refuses it, so that the rules of the case apply). ``source`` (root only) says
        whether the user asked for the rework (``"human"``) or it is root's own reading (``"relayed"``, the default for a rework)."""
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
        """The fields a rework task inherits from the task ``actor`` sent with id ``revises``: ``service`` and ``contract`` of that task and the
        ``playbook`` version current now when it is a service request, and, for an agent, the ``source`` of the open task it received in the
        same trace. Empty when the task is not one of ``actor``'s."""
        ...

    def work_tier(self, actor: str) -> str | None:
        """The tier (``source``) of the work ``actor`` does now, for a task it sends without ``revises``: the ``source`` of its newest open received
        task in the trace its next message is stamped with (the one trace of its open received tasks, else the one trace of its run batch). None for
        root, without such a trace or task, and for a task without a tier."""
        ...
