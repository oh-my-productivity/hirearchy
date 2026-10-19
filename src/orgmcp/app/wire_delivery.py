"""Providers of the ``delivery`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..delivery import MessageDelivery
from ..delivery._pipeline import PipelineMessageDelivery
from ..kernel import Clock, EventSink, IdGenerator, TraceTap
from ..mail import MailboxWriter
from ..traces import TraceStamper
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(
        MessageDelivery,
        lambda b: PipelineMessageDelivery(
            b.get(MailboxWriter), b.get(TraceStamper), b.get(Clock), b.get(IdGenerator), b.get(EventSink), b.get(TraceTap),
        ),
    )
