"""The checks every message passes before it is delivered (moved from ``Org.send``)."""

from __future__ import annotations

from typing import SupportsInt, cast

from ..agents import AgentDirectory
from ..budget import AllocationPolicy
from ..delivery import MessageDelivery
from ..kernel import MESSAGE_TYPES, ROOT, SOURCES, Message, OrgError, norm, parent
from ..settings import OrgSettings
from ._protocols import HopCounter, RoutePolicy
from .api import MessageSender


def provenance_source(
    actor: str, type: str, revises: str | None, feedback: str | None, reply_to: str | None, source: str | None, criterion: str | None,
    inherited: str | None = None,
) -> str | None:
    """Where a message says it comes from (``source``), by the provenance rules every ``MessageSender`` applies (design 5.1):
    only root records ``source`` and ``criterion`` (an agent that passes either is refused, S1), ``source`` is ``human`` or ``relayed`` (S2),
    ``criterion`` goes only on a verdict note (a note with ``feedback``) or a link note (a note that replies to one, S3), and a rework from
    root (a task that ``revises`` another), a verdict note or a link note without a ``source`` is ``relayed``: root's own reading, unless the
    caller says the user asked for it. A fresh task of root, any other note and every message of an agent stay unstamped, except that a task of an
    agent carries ``inherited``, the tier of the work it does (``ReworkContext``: the runtime's copy, never the agent's declaration)."""
    if (source is not None or criterion is not None) and actor != ROOT:
        raise OrgError(
            "only root (the human's seat) records where a verdict, a link or a rework comes from (`source`, `criterion`); "
            "agents' messages carry neither"
        )
    if source is not None and source not in SOURCES:
        raise OrgError('source must be "human" (the user\'s own judgement, in their own words) or "relayed" (anything you concluded yourself)')
    verdict, link = type == "note" and bool(feedback), type == "note" and not feedback and bool(reply_to)
    if criterion is not None and not (verdict or link):
        raise OrgError("criterion goes only on a verdict (a note with `feedback`) or on a link note that replies to one: use `feedback(..., criterion=...)`.")
    if source is None and actor == ROOT and ((type == "task" and revises) or (type == "note" and (feedback or criterion))):
        return "relayed"
    if source is None and actor != ROOT and type == "task" and inherited in SOURCES:
        return inherited
    return source


def check_acknowledges(type: str, feedback: str | None, criterion: str | None, acknowledges: str | None) -> None:
    """``acknowledges`` goes only on a plain note: a note without ``feedback`` and without ``criterion`` (design 9.2). Every ``MessageSender`` applies it."""
    if acknowledges is not None and (type != "note" or feedback or criterion is not None):
        raise OrgError("acknowledges goes only on a plain note")


class RuleMessageSender(MessageSender):
    """Size, type, body, route, budget and hops, in this order; then delivery."""

    def __init__(
        self, agents: AgentDirectory, settings: OrgSettings, routes: RoutePolicy, allocation: AllocationPolicy, hops: HopCounter,
        delivery: MessageDelivery,
    ) -> None:
        self._agents = agents
        self._settings = settings
        self._routes = routes
        self._allocation = allocation
        self._hops = hops
        self._delivery = delivery

    def send(
        self, actor: str, to: str, body: str, *, type: str = "note", title: str = "", reply_to: str | None = None,
        status: str | None = None, budget: int = 0, revises: str | None = None, supersedes: str | None = None,
        service: str | None = None, contract: int | None = None, playbook: int | None = None, feedback: str | None = None,
        source: str | None = None, criterion: str | None = None, wake: bool = True, skip_route_check: bool = False,
        inherited: str | None = None, acknowledges: str | None = None,
    ) -> Message:
        cap = self._settings.message_cap()
        if len(body.strip()) > cap and norm(actor) != ROOT:  # the cap protects agents' runs; the human may paste
            raise OrgError(
                f"message is {len(body.strip())} characters; the limit is {cap} (max_message_chars). Messages are "
                "read in full by the recipient's next run, so keep them short: write the detail to a file inside "
                "your own directory and send a short message that gives its path."
            )
        actor, to = self._agents.require(actor), self._agents.require(to)
        if type not in MESSAGE_TYPES:
            raise OrgError(f"type must be one of {MESSAGE_TYPES}")
        if not body.strip():
            raise OrgError("message body is empty")
        if not skip_route_check and not self._routes.can_message(actor, to, reply_to):
            raise OrgError(
                f"{actor} cannot message {to}: you may message your parent, your direct reports, "
                "your siblings, or whoever sent you the message you are replying to (reply_to)."
            )
        budget = int(budget or 0)
        if budget < 0:
            raise OrgError("budget cannot be negative")
        if budget and actor != ROOT and parent(to) != actor and to != parent(actor):
            raise OrgError("budget can only be handed to your direct reports, or returned to your parent")
        self._allocation.check_allocation(actor, budget, type == "task")
        hops = self._hops.next_hops(actor)
        max_hops = self._settings.config()["max_hops"]
        if type != "result" and hops > int(cast("SupportsInt | str", max_hops)):  # reports always get through
            raise OrgError(
                f"message chain is {hops} hops long (limit {max_hops}); this looks like a loop. "
                "Report blocked to whoever assigned your task instead."
            )
        source = provenance_source(actor, type, revises, feedback, reply_to, source, criterion, inherited)
        check_acknowledges(type, feedback, criterion, acknowledges)
        msg = Message(
            sender=actor, to=to, type=type, body=body.strip(), title=title.strip(),
            reply_to=reply_to, status=status, budget=budget, hops=hops, revises=revises,
            supersedes=supersedes, service=service, contract=contract, playbook=playbook, feedback=feedback,
            source=source, criterion=criterion, wake=wake, acknowledges=acknowledges,
        )
        return self._delivery.deliver(msg)
