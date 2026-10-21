"""``RuleTraceStamper``: which questions it asks its lookup, and in which order, apart from the contract (``test_contract_trace_stamper``)."""

from __future__ import annotations

from hirearchy.kernel import Message
from hirearchy.traces import TraceStamper
from hirearchy.traces._stamper import RuleTraceStamper
from hirearchy.traces.api import TraceLookup

from ._support import message

class ScriptedLookup(TraceLookup):
    """Answers from a script and records the questions."""

    def __init__(self, traces: dict[tuple[str, str], str] | None = None, context: tuple[str | None, str, list[str]] = (None, "ambiguous", [])) -> None:
        self.traces = traces or {}
        self.context = context
        self.asked: list[tuple[str, ...]] = []

    def trace_of(self, addr: str, msg_id: str | None) -> str | None:
        self.asked.append(("trace_of", addr, str(msg_id)))
        return self.traces.get((addr, str(msg_id)))

    def open_task_traces(self, addr: str) -> list[str | None]:
        self.asked.append(("open_task_traces", addr))
        return []

    def context_trace(self, addr: str) -> tuple[str | None, str, list[str]]:
        self.asked.append(("context_trace", addr))
        return self.context


def stamper(lookup: ScriptedLookup) -> TraceStamper:
    return RuleTraceStamper(lookup)


def test_it_is_a_trace_stamper() -> None:
    assert isinstance(stamper(ScriptedLookup()), TraceStamper)


def test_given_and_new_ask_nothing() -> None:
    lookup = ScriptedLookup()
    assert stamper(lookup).stamp(message("runtime", "ceo", "note", trace="T")) == ("given", [])
    assert stamper(lookup).stamp(message("root", "ceo", "task")) == ("new", [])
    assert lookup.asked == []


def test_link_asks_for_reply_to_then_revises_in_the_boxes_of_the_normalized_sender_and_stops_at_the_first_trace() -> None:
    lookup = ScriptedLookup({("ceo", "B"): "TB"})
    msg = message(" ceo/ ", "root", "task", reply_to="A", revises="B")
    assert stamper(lookup).stamp(msg) == ("link", []) and msg.trace == "TB"
    assert lookup.asked == [("trace_of", "ceo", "A"), ("trace_of", "ceo", "B")]
    lookup = ScriptedLookup({("ceo", "A"): "TA", ("ceo", "B"): "TB"})
    stamper(lookup).stamp(message("ceo", "root", "task", reply_to="A", revises="B"))
    assert lookup.asked == [("trace_of", "ceo", "A")]


def test_a_message_without_references_asks_the_lookup_for_the_context_of_the_sender() -> None:
    lookup = ScriptedLookup()
    stamper(lookup).stamp(message("ceo", "root", "note"))
    assert lookup.asked == [("context_trace", "ceo")]


def test_the_rule_and_the_candidates_are_those_of_the_context() -> None:
    contexts: list[tuple[str | None, str, list[str]]] = [("T", "open-task", []), ("T", "batch", []), (None, "ambiguous", ["A", "B"])]
    for context in contexts:
        msg = message("ceo", "root", "note")
        assert stamper(ScriptedLookup(context=context)).stamp(msg) == (context[1], context[2]) and msg.trace == context[0]


def test_the_runtime_asks_nothing_and_is_ambiguous() -> None:
    lookup = ScriptedLookup({("runtime", "A"): "TA"}, context=("T", "batch", []))
    msg: Message = message("runtime", "ceo", "note", reply_to="A")
    assert stamper(lookup).stamp(msg) == ("ambiguous", []) and msg.trace is None and lookup.asked == []
