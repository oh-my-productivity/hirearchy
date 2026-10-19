"""``RecordingDelivery``, the fake of the policy tests: it completes a message like the pipeline and keeps it in a list (apart from the
contract, ``test_contract_message_delivery``)."""

from __future__ import annotations

from orgmcp.delivery import MessageDelivery
from orgmcp.delivery.testing import RecordingDelivery
from orgmcp.kernel import RUNTIME
from orgmcp.kernel.testing import FakeClock, SequenceIdGenerator

from ._support import RED, task


def fake() -> RecordingDelivery:
    clock = FakeClock()
    return RecordingDelivery(clock, SequenceIdGenerator(clock))


def test_it_is_a_message_delivery() -> None:
    assert isinstance(fake(), MessageDelivery)


@RED
def test_it_keeps_every_message_in_order_of_delivery() -> None:
    delivery = fake()
    first = delivery.deliver(task("root", "ceo"))
    note = delivery.notify("ceo", "t", "b")
    second = delivery.deliver(task("ceo", "ceo/eng"))
    assert delivery.messages == [first, note, second]


@RED
def test_what_it_keeps_is_the_message_it_completed() -> None:
    delivery = fake()
    msg = task()
    assert delivery.deliver(msg) is msg and delivery.messages[0] is msg and msg.id and msg.created


@RED
def test_it_has_nothing_to_do_with_the_disk_or_the_events_so_a_message_keeps_its_trace_as_given() -> None:
    delivery = fake()
    assert delivery.deliver(task(trace="T1")).trace == "T1"
    assert delivery.deliver(task()).trace is None  # it stamps no trace of its own: a consumer's test sets the trace it needs


@RED
def test_a_notice_is_a_note_of_the_runtime() -> None:
    msg = fake().notify("ceo", "t", "b", trace="T2")
    assert (msg.sender, msg.type, msg.trace) == (RUNTIME, "note", "T2")
