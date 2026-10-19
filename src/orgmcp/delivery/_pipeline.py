"""The one complete-then-store pipeline for every message (moved from ``Org.deliver`` and ``Org.notify``)."""

from __future__ import annotations

from typing import Any

from ..kernel import RUNTIME, Clock, EventSink, IdGenerator, Message, TraceTap, clip, norm
from ..mail import MailboxWriter
from ..traces import TraceStamper
from .api import MessageDelivery


class PipelineMessageDelivery(MessageDelivery):
    """Completes a message, stores it, and tells the world."""

    def __init__(
        self, mail: MailboxWriter, traces: TraceStamper, clock: Clock, ids: IdGenerator, events: EventSink, tap: TraceTap,
    ) -> None:
        self._mail = mail
        self._traces = traces
        self._clock = clock
        self._ids = ids
        self._events = events
        self._tap = tap

    def deliver(self, msg: Message) -> Message:
        msg.id = msg.id or self._ids.message_id(msg.sender)
        msg.created = msg.created or self._clock.now().isoformat(timespec="seconds")
        try:
            rule, candidates = self._traces.stamp(msg)
        except Exception:  # noqa: BLE001 - a trace is bookkeeping: never worth failing a message for
            rule, candidates = "error", []
        # The sender's copy goes first (MailboxWriter.store): it is what charges a budget grant. A failure between the two writes can then
        # only leave a message charged but undelivered (BatchStore.recover re-delivers it), never delivered but uncharged.
        self._mail.store(msg)
        self._tap.note(msg.trace)
        extra: dict[str, Any] = {"trace_candidates": candidates} if candidates else {}  # Any: only so that mypy lets ** meet the named parameters
        self._events.emit(
            "msg.deliver", actor=msg.sender, trace=msg.trace, id=msg.id, type=msg.type, **{"from": msg.sender},
            to=msg.to, title=clip(msg.title), status=msg.status, budget=msg.budget, reply_to=msg.reply_to,
            revises=msg.revises, supersedes=msg.supersedes, service=msg.service, feedback=msg.feedback,
            wake=msg.wake, hops=msg.hops, chars=len(msg.body), trace_rule=rule, **extra,
        )
        return msg

    def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
        return self.deliver(Message(
            sender=RUNTIME, to=norm(to), type="note", title=title, body=body, wake=wake, trace=trace or None,
        ))
