"""The ``msg.deliver`` event: its fields and their order are the golden shape (``tests/golden``); what the pipeline derives from a message.

``a_message_delivery_with_events*`` of ``tests/test_telemetry.py`` stay as they are (they measure the whole stack)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.delivery.testing import DeliveryHarness, fs_pipeline, memory_pipeline
from orgmcp.delivery._pipeline import PipelineMessageDelivery
from orgmcp.kernel import RUNTIME, Message

from ._fakes import Log, LoggingEvents, LoggingMailbox, LoggingStamper, LoggingTap, CountingClock, CountingIds
from ._support import RED, make, task

# the keys of the event, in this order (the order of the JSON line in the event files)
KEYS = [
    "id", "type", "from", "to", "title", "status", "budget", "reply_to", "revises", "supersedes", "service", "feedback", "wake", "hops",
    "chars", "trace_rule",
]


def deliver_with(stamper: LoggingStamper, msg: Message) -> LoggingEvents:
    log: Log = []
    events = LoggingEvents(log)
    PipelineMessageDelivery(LoggingMailbox(log), stamper, CountingClock(log), CountingIds(log), events, LoggingTap(log)).deliver(msg)
    return events


@RED
def test_the_event_has_the_golden_fields_in_the_golden_order() -> None:
    events = deliver_with(LoggingStamper([], trace="T1", rule="link"), task("ceo", "root", type="result", status="done"))
    (event,) = events.events
    assert event.kind == "msg.deliver" and list(event.fields) == KEYS


@RED
def test_the_event_says_who_delivered_in_which_request() -> None:
    (event,) = deliver_with(LoggingStamper([], trace="T1"), task("ceo/eng", "ceo")).events
    assert (event.actor, event.trace) == ("ceo/eng", "T1")


@RED
def test_the_values_are_those_of_the_message() -> None:
    msg = task(
        "ceo", "ceo/eng", type="task", title="Draft the plan", status=None, budget=3, reply_to="R", revises="V", supersedes="S", service="svc",
        feedback="accept", wake=False, hops=2, body="x" * 61,
    )
    (event,) = deliver_with(LoggingStamper([], trace="T1", rule="open-task"), msg).events
    assert event.fields == {
        "id": "ID-ceo", "type": "task", "from": "ceo", "to": "ceo/eng", "title": "Draft the plan", "status": None, "budget": 3,
        "reply_to": "R", "revises": "V", "supersedes": "S", "service": "svc", "feedback": "accept", "wake": False, "hops": 2, "chars": 61,
        "trace_rule": "open-task",
    }


@RED
def test_the_title_is_clipped_to_eighty_characters_and_the_body_is_only_counted() -> None:
    (event,) = deliver_with(LoggingStamper([]), task(title="t" * 100, body="b" * 5000)).events
    assert event.fields["title"] == "t" * 79 + "…" and event.fields["chars"] == 5000
    assert "body" not in event.fields


@RED
def test_the_candidates_of_an_ambiguous_message_come_last() -> None:
    stamper = LoggingStamper([], trace=None, rule="ambiguous", candidates=["T1", "T2"])
    (event,) = deliver_with(stamper, task("ceo", "root", type="note")).events
    assert list(event.fields) == [*KEYS, "trace_candidates"] and event.fields["trace_candidates"] == ["T1", "T2"] and event.trace is None


@RED
def test_without_candidates_the_key_is_absent() -> None:
    (event,) = deliver_with(LoggingStamper([]), task()).events
    assert "trace_candidates" not in event.fields


@RED
def test_a_notice_of_the_runtime_is_an_event_of_the_runtime() -> None:
    (event,) = deliver_with(LoggingStamper([], trace=None, rule="ambiguous"), task(RUNTIME, "ceo", type="note")).events
    assert (event.actor, event.fields["from"]) == (RUNTIME, RUNTIME)


@RED
def test_one_event_per_message() -> None:
    log: Log = []
    events = LoggingEvents(log)
    delivery = PipelineMessageDelivery(LoggingMailbox(log), LoggingStamper(log), CountingClock(log), CountingIds(log), events, LoggingTap(log))
    for _ in range(3):
        delivery.deliver(task())
    assert [e.kind for e in events.events] == ["msg.deliver"] * 3


# ------------------------------------------------------------------------------ with the real stamper, over both mailboxes


@pytest.fixture(params=[fs_pipeline, memory_pipeline], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> DeliveryHarness:
    return make(request, tmp_path)


@RED
def test_a_task_of_the_human_starts_a_trace_and_the_event_says_so(h: DeliveryHarness) -> None:
    assert h.events is not None and h.tap is not None
    msg = h.delivery.deliver(task("root", "ceo"))
    (event,) = h.events.events
    assert msg.trace == msg.id and (event.trace, event.fields["trace_rule"]) == (msg.id, "new")
    assert h.tap.notes == [msg.id]


@RED
def test_an_answer_joins_the_trace_of_the_task_it_answers(h: DeliveryHarness) -> None:
    assert h.events is not None
    first = h.delivery.deliver(task("root", "ceo"))
    answer = h.delivery.deliver(task("ceo", "root", type="result", reply_to=first.id, status="done"))
    assert answer.trace == first.id
    assert [e.fields["trace_rule"] for e in h.events.events] == ["new", "link"]


@RED
def test_a_notice_about_a_task_keeps_the_trace_it_is_given(h: DeliveryHarness) -> None:
    assert h.events is not None
    h.delivery.notify("ceo", "t", "b", trace="T5")
    (event,) = h.events.events
    assert (event.trace, event.fields["trace_rule"]) == ("T5", "given")
