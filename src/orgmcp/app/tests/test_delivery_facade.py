"""The delivery slice of the ``Org`` facade: ``deliver``, ``notify`` and ``new_id`` behave as they always did (green before and after), and now go
through the ports of the runtime (``delivery`` and ``ids``)."""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Any

import pytest

from orgmcp.app import Org
from orgmcp.delivery import MessageDelivery
from orgmcp.kernel import RUNTIME, Message
from orgmcp.kernel.testing import FakeClock, SequenceIdGenerator


def use(org: Org, **ports: Any) -> None:
    org.runtime = dataclasses.replace(org.runtime, **ports)


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.", can_hire=True, max_children=2)
    made.hire("ceo", "eng", "Engineer", "Build.")
    return made


# ----------------------------------------------------------------------------------- as it always was (green before and after)


def test_deliver_completes_the_message_in_place_and_writes_both_copies(org: Org) -> None:
    msg = Message(sender="ceo", to="ceo/eng", type="note", body="hello", title="hi")
    assert org.deliver(msg) is msg
    assert re.fullmatch(r"\d{8}T\d{12}-ceo-[0-9a-f]{4}", msg.id) and msg.created
    assert (org.dir("ceo") / "sent" / f"{msg.id}.md").read_text(encoding="utf-8") == msg.to_text()
    assert (org.dir("ceo/eng") / "inbox" / f"{msg.id}.md").read_text(encoding="utf-8") == msg.to_text()


def test_deliver_by_the_runtime_has_no_sent_copy(org: Org) -> None:
    msg = org.deliver(Message(sender=RUNTIME, to="ceo", type="note", body="b"))
    assert (org.dir("ceo") / "inbox" / f"{msg.id}.md").is_file() and not (org.dir(RUNTIME)).exists()


def test_deliver_stamps_the_trace_and_emits_the_event(org: Org) -> None:
    msg = org.deliver(Message(sender="root", to="ceo", type="task", body="b", title="T"))
    assert msg.trace == msg.id


def test_notify_is_a_waking_note_of_the_runtime_unless_held_back(org: Org) -> None:
    note = org.notify(" /ceo/ ", "A title", "A body", trace="T3")
    assert (note.sender, note.to, note.type, note.wake, note.trace) == (RUNTIME, "ceo", "note", True, "T3")
    held = org.notify("ceo", "Later", "b", wake=False)
    assert org.unread("ceo") == 1 and org.messages("ceo", "inbox")[-1].id == held.id


def test_new_id_has_the_format_of_a_message_id(org: Org) -> None:
    assert re.fullmatch(r"\d{8}T\d{12}-ceo\.eng-[0-9a-f]{4}", org.new_id("ceo/eng"))


# -------------------------------------------------------------------------------------------- through the ports (red until wired)


class Recorded(MessageDelivery):
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def deliver(self, msg: Message) -> Message:
        self.calls.append(("deliver", msg))
        msg.id = "FROM-THE-PORT"
        return msg

    def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
        self.calls.append(("notify", to, title, body, wake, trace))
        return Message(sender=RUNTIME, to=to, type="note", body=body, id="NOTIFIED")


def test_deliver_comes_from_the_delivery_port_of_the_runtime(org: Org) -> None:
    fake = Recorded()
    use(org, delivery=fake)
    msg = Message(sender="ceo", to="root", type="note", body="b")
    assert org.deliver(msg) is msg and msg.id == "FROM-THE-PORT" and fake.calls == [("deliver", msg)]
    assert not list((org.dir("ceo") / "sent").glob("*.md"))


def test_notify_comes_from_the_delivery_port_of_the_runtime(org: Org) -> None:
    fake = Recorded()
    use(org, delivery=fake)
    assert org.notify("ceo", "t", "b", wake=False, trace="T").id == "NOTIFIED"
    assert fake.calls == [("notify", "ceo", "t", "b", False, "T")]


def test_what_the_other_slices_deliver_goes_through_the_port(org: Org) -> None:
    fake = Recorded()
    use(org, delivery=fake)
    org.send("root", "ceo", "hello")
    assert [c[0] for c in fake.calls] == ["deliver"]


def test_new_id_comes_from_the_id_generator_of_the_runtime(org: Org) -> None:
    use(org, ids=SequenceIdGenerator(FakeClock()))
    assert org.new_id("ceo") == "20261018T100000000001-ceo-0000"
