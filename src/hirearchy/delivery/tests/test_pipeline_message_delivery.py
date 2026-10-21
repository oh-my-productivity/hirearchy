"""``PipelineMessageDelivery``: what it asks of each collaborator, and in which order (ARCHITECTURE.md 10.1, risk 3), apart from the contract
(``test_contract_message_delivery``)."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from hirearchy.delivery import MessageDelivery
from hirearchy.delivery._pipeline import PipelineMessageDelivery
from hirearchy.kernel import RUNTIME
from hirearchy.traces import TraceStamper

from ._fakes import (
    CountingClock,
    CountingIds,
    FailingStamper,
    GivenStamper,
    Log,
    LoggingEvents,
    LoggingMailbox,
    LoggingStamper,
    LoggingTap,
)
from ._support import task


class Rig:
    """A pipeline over doubles that share one log."""

    def __init__(self, stamper: Callable[[Log], TraceStamper] = LoggingStamper, store_fails: Exception | None = None) -> None:
        self.log: Log = []
        self.mail = LoggingMailbox(self.log, store_fails)
        self.stamper = stamper(self.log)
        self.clock = CountingClock(self.log)
        self.ids = CountingIds(self.log)
        self.events = LoggingEvents(self.log)
        self.tap = LoggingTap(self.log)
        self.delivery = PipelineMessageDelivery(self.mail, self.stamper, self.clock, self.ids, self.events, self.tap)


def test_it_is_a_message_delivery() -> None:
    assert isinstance(Rig().delivery, MessageDelivery)


# ------------------------------------------------------------------------------ the order


def test_the_order_is_id_then_time_then_stamp_then_store_then_note_then_event() -> None:
    rig = Rig()
    rig.delivery.deliver(task())
    assert rig.log == ["id", "clock", "stamp", "store", "note", "emit"]


def test_nothing_is_asked_for_an_id_and_a_time_that_are_set() -> None:
    rig = Rig()
    rig.delivery.deliver(task(id="I", created="C"))
    assert rig.log == ["stamp", "store", "note", "emit"]


def test_only_the_missing_one_of_the_two_is_made() -> None:
    rig = Rig()
    rig.delivery.deliver(task(id="I"))
    assert rig.log[:2] == ["clock", "stamp"] and rig.ids.asked == []
    other = Rig()
    other.delivery.deliver(task(created="C"))
    assert other.log[:2] == ["id", "stamp"] and other.clock.calls == 0


def test_the_id_is_made_for_the_sender_as_written() -> None:
    rig = Rig()
    msg = rig.delivery.deliver(task("ceo/eng", "ceo"))
    assert rig.ids.asked == ["ceo/eng"] and msg.id == "ID-ceo/eng"


def test_the_time_is_the_clock_to_the_second() -> None:
    assert Rig().delivery.deliver(task()).created == "2030-05-06T07:08:09+00:00"


def test_the_stamper_sees_the_message_with_its_id_and_time() -> None:
    rig = Rig()
    rig.delivery.deliver(task())
    assert isinstance(rig.stamper, LoggingStamper) and rig.stamper.saw == [("ID-root", "2030-05-06T07:08:09+00:00")]


def test_what_is_stored_carries_the_stamped_trace() -> None:
    rig = Rig(lambda log: LoggingStamper(log, trace="T-STAMPED"))
    rig.delivery.deliver(task())
    assert rig.mail.traces_seen == ["T-STAMPED"] and rig.mail.stored[0].trace == "T-STAMPED"


def test_the_trace_noted_on_the_tool_call_is_the_one_stamped() -> None:
    rig = Rig(lambda log: LoggingStamper(log, trace="T-STAMPED"))
    rig.delivery.deliver(task())
    assert rig.tap.notes == ["T-STAMPED"]


def test_an_unstamped_message_notes_none() -> None:
    rig = Rig(lambda log: LoggingStamper(log, trace=None, rule="ambiguous"))
    rig.delivery.deliver(task())
    assert rig.tap.notes == [None]


# ------------------------------------------------------------------------------ a stamping exception never blocks a message


def test_a_stamping_exception_does_not_stop_the_message() -> None:
    rig = Rig(FailingStamper)
    msg = rig.delivery.deliver(task())
    assert rig.mail.stored == [msg] and msg.trace is None
    assert rig.log == ["id", "clock", "stamp", "store", "note", "emit"]


def test_a_stamping_exception_is_the_rule_error_without_candidates() -> None:
    rig = Rig(FailingStamper)
    rig.delivery.deliver(task())
    (event,) = rig.events.events
    assert event.fields["trace_rule"] == "error" and "trace_candidates" not in event.fields and event.trace is None
    assert rig.tap.notes == [None]


@pytest.mark.parametrize("error", [ValueError("x"), OSError("disk"), KeyError("k"), RuntimeError("r")])
def test_any_ordinary_exception_while_stamping_is_swallowed(error: Exception) -> None:
    rig = Rig(lambda log: FailingStamper(log, error))
    assert rig.delivery.deliver(task()).id == "ID-root"


# ------------------------------------------------------------------------------ a write that fails


def test_a_failing_store_raises_and_nothing_follows_it() -> None:
    rig = Rig(store_fails=OSError(28, "No space left on device"))
    with pytest.raises(OSError):
        rig.delivery.deliver(task())
    assert rig.log == ["id", "clock", "stamp", "store"]
    assert rig.events.events == [] and rig.tap.notes == []


def test_the_message_is_completed_in_place_even_when_the_store_fails() -> None:
    rig = Rig(store_fails=OSError("disk"))
    msg = task()
    with pytest.raises(OSError):
        rig.delivery.deliver(msg)
    assert msg.id == "ID-root" and msg.created and msg.trace == "T1"


# ------------------------------------------------------------------------------ notify


def test_notify_delivers_a_note_of_the_runtime_through_the_same_pipeline() -> None:
    rig = Rig(lambda log: GivenStamper())
    msg = rig.delivery.notify(" /ceo/ ", "Title", "Body", wake=False, trace="T9")
    assert rig.mail.stored == [msg]
    assert (msg.sender, msg.to, msg.type, msg.title, msg.body, msg.wake, msg.trace) == (RUNTIME, "ceo", "note", "Title", "Body", False, "T9")
    assert rig.log == ["id", "clock", "store", "note", "emit"]
    assert rig.ids.asked == [RUNTIME] and rig.tap.notes == ["T9"]


def test_notify_without_a_trace_leaves_the_decision_to_the_stamper() -> None:
    rig = Rig(lambda log: GivenStamper())
    for trace in (None, ""):
        assert rig.delivery.notify("ceo", "t", "b", trace=trace).trace is None
    assert [e.fields["trace_rule"] for e in rig.events.events] == ["ambiguous", "ambiguous"]


def test_notify_wakes_by_default() -> None:
    assert Rig().delivery.notify("ceo", "t", "b").wake is True
