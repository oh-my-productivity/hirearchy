"""RED skeleton (B-delivery): the complete-then-store pipeline."""

from __future__ import annotations

from ..kernel import Clock, EventSink, IdGenerator, Message, TraceTap
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
        raise NotImplementedError("red: B-delivery")

    def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
        raise NotImplementedError("red: B-delivery")
