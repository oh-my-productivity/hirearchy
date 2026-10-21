"""``RecordingSender``, the fake of the consumers' tests: it keeps what it is asked to send (apart from the contract, ``test_contract_message_sender``)."""

from __future__ import annotations

from hirearchy.delivery.testing import RecordingDelivery
from hirearchy.dispatch.testing import FixedReworkContext, NoReworkContext, RecordingSender
from hirearchy.kernel.testing import FakeClock, SequenceIdGenerator


def fake() -> RecordingSender:
    clock = FakeClock()
    return RecordingSender(RecordingDelivery(clock, SequenceIdGenerator(clock)))


def test_it_keeps_every_message_in_order_of_sending() -> None:
    sender = fake()
    first = sender.send("root", "ceo", "one")
    second = sender.send("ceo", "ceo/eng", "two", type="task", budget=3)
    assert sender.messages == [first, second] and second.budget == 3


def test_it_checks_nothing() -> None:
    sender = fake()
    msg = sender.send("ghost", "nobody", "x" * 100000, type="bogus", budget=-4)
    assert (msg.sender, msg.to, msg.type, msg.budget) == ("ghost", "nobody", "bogus", -4)


def test_it_remembers_the_messages_the_route_check_was_skipped_for() -> None:
    sender = fake()
    sender.send("ceo", "root", "a")
    skipped = sender.send("ceo", "root", "b", type="result", skip_route_check=True)
    assert sender.route_check_skipped == [skipped.id]


def test_the_rework_stand_ins_answer_with_nothing_or_with_what_they_were_given() -> None:
    assert dict(NoReworkContext().fields_for("ceo", "x")) == {}
    assert dict(FixedReworkContext({"x": {"service": "s"}}).fields_for("ceo", "x")) == {"service": "s"}
    assert dict(FixedReworkContext({"x": {"service": "s"}}).fields_for("ceo", "y")) == {}
