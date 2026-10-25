"""A manager gives a task to a direct report (moved from ``Org.delegate``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypedDict

from ..agents import AgentDirectory
from ..budget import AllocationPolicy
from ..kernel import ROOT, Message, OrgError, parent
from ..mail import MailboxReader
from ..templates import DocumentTemplates
from .api import MessageSender, ReworkContext, TaskAssigner

USE_REQUEST = (  # P4-USE-REQUEST
    "refused: {revises} is a request for the service `{service}`: send it back with request(service=\"{service}\", inputs=..., "
    "revises=\"{revises}\", source=...) (CLI: hirearchy request {service} --revises {revises}) so the rework stays in its case under the "
    "contract (and names its base when a relayed rework changed the delivery). Nothing was sent."
)


class _ServiceFields(TypedDict, total=False):
    """The fields of a task that a rework of a service request inherits."""

    service: str | None
    contract: int | None
    playbook: int | None


def _service_fields(fields: Mapping[str, object]) -> _ServiceFields:
    """The service fields among what a ``ReworkContext`` answered (the fields it did not name are left out)."""
    found: _ServiceFields = {}
    service, contract, playbook = fields.get("service"), fields.get("contract"), fields.get("playbook")
    if "service" in fields:
        found["service"] = service if isinstance(service, str) else None
    if "contract" in fields:
        found["contract"] = contract if isinstance(contract, int) and not isinstance(contract, bool) else None
    if "playbook" in fields:
        found["playbook"] = playbook if isinstance(playbook, int) and not isinstance(playbook, bool) else None
    return found


def _tier_of(fields: Mapping[str, object]) -> str | None:
    """The tier (``source``) a ``ReworkContext`` answered, when it is a string."""
    tier = fields.get("source")
    return tier if isinstance(tier, str) else None


class RuleTaskAssigner(TaskAssigner):
    """Direct reports only; a title, a goal and acceptance criteria; a budget of at least one run."""

    def __init__(
        self, agents: AgentDirectory, mail: MailboxReader, templates: DocumentTemplates, allocation: AllocationPolicy,
        rework: ReworkContext, sender: MessageSender,
    ) -> None:
        self._agents = agents
        self._mail = mail
        self._templates = templates
        self._allocation = allocation
        self._rework = rework
        self._sender = sender

    def delegate(
        self, actor: str, to: str, title: str, goal: str, acceptance: str, inputs: Sequence[str] | None = None,
        budget: int | None = None, revises: str | None = None, source: str | None = None,
    ) -> Message:
        actor, to = self._agents.require(actor), self._agents.require(to)
        if actor != ROOT and parent(to) != actor:
            reports = ", ".join(self._agents.children(actor)) or "none (hire one first)"
            raise OrgError(f"you can only delegate to your direct reports: {reports}")
        if not title.strip() or not goal.strip() or not acceptance.strip():
            raise OrgError("a task needs a title, a goal and acceptance criteria")
        if budget is None:
            budget = self._allocation.default_budget(actor)
        budget = int(budget)
        if budget < 1:
            raise OrgError("a task needs a budget of at least 1 run")
        if revises and not any(m.id == revises and m.type == "task" and m.to == to for m in self._mail.sent(actor)):
            raise OrgError(f"revises must be the id of an earlier task you sent to {to}: {revises}")
        body = self._templates.task_body(goal, acceptance, list(inputs or []))
        fields = self._rework.fields_for(actor, revises) if revises else {}  # rework of a service request is still part of its case
        inherited = _tier_of(fields) if revises else (self._work_tier(actor) if actor != ROOT else None)  # an agent's fresh task carries the tier of its work (F-E6-7)
        service = fields.get("service")
        if actor == ROOT and revises and isinstance(service, str) and service:  # root's rework of a request goes through ``request``, which keeps the rules of the case
            raise OrgError(USE_REQUEST.format(revises=revises, service=service))
        return self._sender.send(
            actor, to, body, type="task", title=title, budget=budget, revises=revises or None,
            source=source, inherited=inherited, **_service_fields(fields),
        )

    def _work_tier(self, actor: str) -> str | None:
        """The tier of the work ``actor`` does now; None when the mailboxes cannot be read (the delegation is sent as it was: the tier is advice)."""
        try:
            return self._rework.work_tier(actor)
        except (OrgError, OSError):
            return None
