"""Contract of ``MessageDelivery``: the pipeline over the mailboxes on disk, over the in-memory ones, and the recording fake behave alike.

What the callers rely on: ``deliver`` completes the message in place and returns it, the sender's copy and the recipient's copy are the same
file text, the runtime has no sent copy, and ``notify`` is a note from the runtime."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from orgmcp.delivery import MessageDelivery
from orgmcp.delivery.testing import IMPLEMENTATIONS, DeliveryHarness
from orgmcp.kernel import RUNTIME, Message

from ._support import RED, make, task

pytestmark = RED


@pytest.fixture(params=IMPLEMENTATIONS[MessageDelivery], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> DeliveryHarness:
    made = make(request, tmp_path)
    assert isinstance(made.delivery, MessageDelivery)
    return made


# ------------------------------------------------------------------------------ deliver completes the message in place


def test_deliver_returns_the_message_it_was_given_completed(h: DeliveryHarness) -> None:
    msg = task()
    assert h.delivery.deliver(msg) is msg
    assert msg.id and msg.created


def test_the_id_has_the_format_of_a_message_id(h: DeliveryHarness) -> None:
    msg = h.delivery.deliver(task("ceo/eng", "ceo"))
    assert re.fullmatch(r"\d{8}T\d{12}-ceo\.eng-[0-9a-f]{4}", msg.id)


def test_created_is_the_time_of_the_clock_to_the_second(h: DeliveryHarness) -> None:
    msg = h.delivery.deliver(task())
    assert msg.created == "2026-10-18T10:00:00+00:00"
    h.clock.advance(65)
    assert h.delivery.deliver(task()).created == "2026-10-18T10:01:05+00:00"


def test_an_id_and_a_creation_time_that_are_set_are_kept(h: DeliveryHarness) -> None:
    msg = task(id="20260101T000000000001-root-aaaa", created="2026-01-01T00:00:00+00:00")
    h.delivery.deliver(msg)
    assert (msg.id, msg.created) == ("20260101T000000000001-root-aaaa", "2026-01-01T00:00:00+00:00")
    assert [m.id for m in h.inbox("ceo")] == ["20260101T000000000001-root-aaaa"]


def test_the_ids_of_successive_messages_are_ordered_and_distinct(h: DeliveryHarness) -> None:
    ids = [h.delivery.deliver(task()).id for _ in range(5)]
    assert ids == sorted(ids) and len(set(ids)) == 5


# ------------------------------------------------------------------------------ and stores it


def test_the_recipient_has_the_message_and_the_sender_has_a_copy(h: DeliveryHarness) -> None:
    msg = h.delivery.deliver(task("root", "ceo"))
    assert [m.to_text() for m in h.inbox("ceo")] == [msg.to_text()]
    assert [m.to_text() for m in h.sent("root")] == [msg.to_text()]


def test_an_agent_sender_has_its_copy_in_its_own_boxes(h: DeliveryHarness) -> None:
    msg = h.delivery.deliver(task("ceo/eng", "ceo"))
    assert [m.id for m in h.sent("ceo/eng")] == [msg.id] and [m.id for m in h.inbox("ceo")] == [msg.id]
    assert h.inbox("ceo/eng") == [] and h.sent("ceo") == []


def test_the_human_receives_like_an_agent(h: DeliveryHarness) -> None:
    msg = h.delivery.deliver(task("ceo", "root"))
    assert [m.id for m in h.inbox("root")] == [msg.id]


def test_the_runtime_has_no_sent_copy(h: DeliveryHarness) -> None:
    msg = h.delivery.deliver(Message(sender=RUNTIME, to="ceo", type="note", body="b", title="t"))
    assert [m.id for m in h.inbox("ceo")] == [msg.id] and h.sent(RUNTIME) == []


def test_every_message_is_delivered_once(h: DeliveryHarness) -> None:
    first, second = h.delivery.deliver(task()), h.delivery.deliver(task())
    assert [m.id for m in h.inbox("ceo")] == [first.id, second.id]


# ------------------------------------------------------------------------------ notify


def test_notify_is_a_waking_note_from_the_runtime(h: DeliveryHarness) -> None:
    msg = h.delivery.notify("ceo", "A title", "The body.")
    assert (msg.sender, msg.to, msg.type, msg.title, msg.body, msg.wake) == (RUNTIME, "ceo", "note", "A title", "The body.", True)
    assert msg.id and msg.created and msg.trace is None


def test_notify_may_hold_the_note_back(h: DeliveryHarness) -> None:
    assert h.delivery.notify("ceo", "t", "b", wake=False).wake is False
    assert h.delivery.notify("ceo", "t", "b").wake is True


def test_notify_carries_the_trace_it_is_given(h: DeliveryHarness) -> None:
    assert h.delivery.notify("ceo", "t", "b", trace="T7").trace == "T7"
    assert h.delivery.notify("ceo", "t", "b", trace="").trace is None
    assert h.delivery.notify("ceo", "t", "b", trace=None).trace is None


def test_notify_normalizes_the_address_and_delivers(h: DeliveryHarness) -> None:
    msg = h.delivery.notify(" /ceo/eng/ ", "t", "b")
    assert msg.to == "ceo/eng" and [m.id for m in h.inbox("ceo/eng")] == [msg.id]
    assert h.delivery.notify("", "t", "b").to == "root" and h.delivery.notify("root", "t", "b").to == "root"


def test_a_notice_has_no_sent_copy(h: DeliveryHarness) -> None:
    h.delivery.notify("ceo", "t", "b")
    assert h.sent(RUNTIME) == []
