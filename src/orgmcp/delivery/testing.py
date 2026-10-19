"""The delivery pipeline over the mailboxes on disk and over the in-memory ones, and the recording fake: what the contract suite iterates over.

``RecordingDelivery`` is the fake every policy test of a consumer uses (``dispatch``, ``hierarchy``, ``budget``): it completes a message the way
the pipeline does and keeps it in a list instead of the boxes. ``DeliveryHarness`` is what a test gets: the delivery under test, the means to see
what it delivered (``inbox``, ``sent``), and the recorders of the events and of the traces it noted.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..kernel import RUNTIME, Clock, IdGenerator, Message
from ..kernel.testing import FakeClock, ListEventSink, RecordingTraceTap, SequenceIdGenerator
from ..mail.testing import MailHarness
from ..traces.testing import TraceHarness, fs_traces, memory_traces
from ._pipeline import PipelineMessageDelivery
from .api import MessageDelivery


class RecordingDelivery(MessageDelivery):
    """RED skeleton (B-delivery): delivery that keeps the messages in a list."""

    def __init__(self, clock: Clock, ids: IdGenerator) -> None:
        self._clock = clock
        self._ids = ids
        self.messages: list[Message] = []

    def deliver(self, msg: Message) -> Message:
        raise NotImplementedError("red: B-delivery")

    def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
        raise NotImplementedError("red: B-delivery")


@dataclass(frozen=True)
class DeliveryHarness:
    """A delivery and the means to look at what it did."""

    delivery: MessageDelivery
    inbox: Callable[[str], list[Message]]  # what was delivered to an address
    sent: Callable[[str], list[Message]]  # what an address (not the runtime) sent
    events: ListEventSink | None  # the events it emitted (None: it emits none)
    tap: RecordingTraceTap | None  # the traces it noted (None: it notes none)
    clock: FakeClock
    mail: MailHarness | None  # the mailboxes behind it, when there are some


def _pipeline(traces: TraceHarness) -> DeliveryHarness:
    clock = FakeClock()
    events, tap = ListEventSink(), RecordingTraceTap()
    delivery = PipelineMessageDelivery(traces.mail.writer, traces.stamper, clock, SequenceIdGenerator(clock), events, tap)
    reader = traces.mail.reader
    return DeliveryHarness(
        delivery, lambda addr: reader.messages(addr, "inbox"), lambda addr: reader.messages(addr, "sent"), events, tap, clock, traces.mail,
    )


def fs_pipeline(tmp_path: Path) -> DeliveryHarness:
    return _pipeline(fs_traces(tmp_path))


def memory_pipeline(tmp_path: Path) -> DeliveryHarness:
    return _pipeline(memory_traces(tmp_path))


def recording_delivery(tmp_path: Path) -> DeliveryHarness:
    clock = FakeClock()
    fake = RecordingDelivery(clock, SequenceIdGenerator(clock))
    return DeliveryHarness(
        fake, lambda addr: [m for m in fake.messages if m.to == addr],
        lambda addr: [m for m in fake.messages if m.sender == addr and m.sender != RUNTIME], None, None, clock, None,
    )


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    MessageDelivery: [fs_pipeline, memory_pipeline, recording_delivery],
}
