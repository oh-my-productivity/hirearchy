"""``wire_delivery``: the runtime has the delivery port, built from the mailbox writer, trace stamper, clock, id generator, event sink and trace tap
of the runtime."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.app import wiring
from orgmcp.delivery import MessageDelivery
from orgmcp.delivery._pipeline import PipelineMessageDelivery
from orgmcp.kernel import Clock, EventSink, IdGenerator, Message, TraceTap
from orgmcp.kernel.testing import FakeClock, ListEventSink, RecordingTraceTap, SequenceIdGenerator
from orgmcp.mail import MailboxWriter
from orgmcp.mail.testing import MemoryMailbox
from orgmcp.traces import TraceStamper


class GivenStamper(TraceStamper):
    def stamp(self, msg: Message) -> tuple[str, list[str]]:
        return ("given", []) if msg.trace else ("ambiguous", [])


def test_the_runtime_has_the_delivery_port(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.delivery, PipelineMessageDelivery) and isinstance(runtime.delivery, MessageDelivery)


def test_building_the_port_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.delivery is not None
    assert list(tmp_path.iterdir()) == []


def test_every_collaborator_comes_from_the_runtime(tmp_path: Path) -> None:
    mail, events, tap = MemoryMailbox(), ListEventSink(), RecordingTraceTap()
    clock = FakeClock()
    overrides: dict[type, object] = {
        MailboxWriter: mail, TraceStamper: GivenStamper(), Clock: clock, IdGenerator: SequenceIdGenerator(clock), EventSink: events, TraceTap: tap,
    }
    runtime = wiring.open_runtime(tmp_path, overrides)
    msg = runtime.delivery.deliver(Message(sender="root", to="ceo", type="note", body="b", trace="T1"))
    assert msg.id.startswith("20261018T100000") and msg.created == "2026-10-18T10:00:00+00:00"
    assert mail.agents.read(f"ceo/inbox/{msg.id}.md") == msg.to_text() and mail.agents.read(f"sent/{msg.id}.md") == msg.to_text()
    assert tap.notes == ["T1"] and [e.kind for e in events.events] == ["msg.deliver"]


def test_the_real_pipeline_writes_the_two_copies_under_the_root(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    msg = runtime.delivery.deliver(Message(sender="root", to="ceo", type="note", body="b"))
    assert (tmp_path / "sent" / f"{msg.id}.md").is_file() and (tmp_path / "ceo" / "inbox" / f"{msg.id}.md").is_file()


def test_an_override_replaces_the_port(tmp_path: Path) -> None:
    class Nothing(MessageDelivery):
        def deliver(self, msg: Message) -> Message:
            return msg

        def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
            return Message(sender="runtime", to=to, type="note", body=body)

    fake = Nothing()
    assert wiring.open_runtime(tmp_path, {MessageDelivery: fake}).delivery is fake


def test_every_runtime_has_its_own_delivery(tmp_path: Path) -> None:
    assert wiring.open_runtime(tmp_path).delivery is not wiring.open_runtime(tmp_path).delivery
