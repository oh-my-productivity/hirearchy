"""Provenance on a message: ``source`` and ``criterion`` (stored after ``feedback``, before ``trace``), ``SOURCES``,
``verdict_tier`` and ``link_ids``. The fields are plain values here; who may set them is the dispatch sender's rule."""

from __future__ import annotations

from dataclasses import fields

import pytest

import hirearchy.kernel as kernel
from hirearchy.kernel import Message

MID = "20261018T100000000001-root-ab12"


def verdict(**kw: object) -> Message:
    return Message("root", "ceo", "note", "keep it", feedback="accept", reply_to="t1", id=MID, created="c", **kw)  # type: ignore[arg-type]


def test_a_root_note_without_source_reads_human() -> None:
    assert kernel.SOURCES == ("human", "relayed")
    assert kernel.verdict_tier(verdict()) == "human"  # a note written before sources existed
    assert kernel.verdict_tier(Message("root", "ceo", "note", "x", id=MID)) == "human"


@pytest.mark.parametrize(("source", "tier"), [("human", "human"), ("relayed", "relayed"), ("garbage", "relayed"), ("HUMAN", "relayed")])
def test_source_human_and_relayed_are_read_as_given_and_an_unknown_value_as_relayed(source: str, tier: str) -> None:
    assert kernel.verdict_tier(verdict(source=source)) == tier


def test_a_note_from_an_agent_reads_agent() -> None:
    note = Message("ceo", "ceo/eng", "note", "no", feedback="reject", reply_to="t1", id=MID)
    assert kernel.verdict_tier(note) == "agent"
    note.source = "human"  # a hand-edited file: an agent's note never weighs as the user's
    assert kernel.verdict_tier(note) == "agent"


@pytest.mark.parametrize(
    ("raw", "ids"),
    [("C6, R2", ("C6", "R2")), ("C6,R2", ("C6", "R2")), ("C6", ("C6",)), ("none", ("none",)), (None, ()), ("", ()), (" , C1,, ", ("C1",))],
)
def test_link_ids_split_on_commas_in_order_without_blanks(raw: str | None, ids: tuple[str, ...]) -> None:
    assert kernel.link_ids(verdict(criterion=raw)) == ids


def test_a_message_without_the_fields_is_stored_byte_for_byte_as_before() -> None:
    m = Message("root", "ceo", "note", "keep it", feedback="accept", reply_to="t1", id="i1", created="2026-10-18T10:00:00")
    assert m.to_text() == (
        "---\nid: i1\nfrom: root\nto: ceo\ntype: note\ntitle: ''\ncreated: '2026-10-18T10:00:00'\nhops: 0\nreply_to: t1\nfeedback: accept\n---\nkeep it\n"
    )
    assert "source" not in m.meta() and "criterion" not in m.meta()
    assert Message.parse(m.to_text()) == m


def test_source_and_criterion_are_stored_after_feedback_and_before_trace() -> None:
    m = Message("root", "ceo", "note", "about C6", feedback="reject", source="human", criterion="C6, R2", trace="tr", reply_to="t1",
                id="i1", created="c")
    keys = list(m.meta())
    assert keys[-4:] == ["feedback", "source", "criterion", "trace"]
    assert m.meta()["source"] == "human" and m.meta()["criterion"] == "C6, R2"
    back = Message.parse(m.to_text())
    assert back == m and (back.source, back.criterion) == ("human", "C6, R2")
    assert Message.parse("---\nfrom: root\nsource: ''\ncriterion: ''\n---\nb").source is None


def test_the_header_shows_source_and_criterion_after_feedback_only_when_set() -> None:
    plain = Message("root", "ceo", "note", "n", feedback="reject", id="n1")
    assert plain.render() == "### note n1\nfrom: root | to: ceo | feedback: reject\n\nn\n"
    full = Message("root", "ceo", "task", "t", feedback="reject", source="relayed", criterion="C6", budget=2, id="n2")
    assert full.render() == "### task n2\nfrom: root | to: ceo | feedback: reject | source: relayed | criterion: C6 | budget: 2 runs\n\nt\n"
    assert Message("root", "ceo", "task", "t", source="human", id="n3").render() == "### task n3\nfrom: root | to: ceo | source: human\n\nt\n"


def test_the_dataclass_declares_source_and_criterion_between_feedback_and_trace() -> None:
    names = [f.name for f in fields(Message)]
    assert names[names.index("feedback") : names.index("trace") + 1] == ["feedback", "source", "criterion", "trace"]
    assert Message("a", "b", "note", "x").source is None and Message("a", "b", "note", "x").criterion is None
