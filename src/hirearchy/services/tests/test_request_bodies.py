"""``TextRequestBodies``: the body of a request, as markdown."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from hirearchy.services import Contract, number_criteria
from hirearchy.services._request import TextRequestBodies

BODIES = TextRequestBodies()


def body(c: Contract, given: Mapping[str, str], extra: Sequence[str], note: str) -> str:
    """The body of a request for ``c``, whose criteria carry the ids of a contract that never changed (C1, C2, ...)."""
    return BODIES.body(c, number_criteria([(1, "root", c.acceptance)]), given, extra, note)


def contract(**over: object) -> Contract:
    base: dict[str, object] = dict(
        name="brief", owner="ceo", description="A brief.", inputs=[{"name": "topic", "description": "t", "required": True}, {"name": "week", "description": "", "required": False}],
        acceptance=["Short"], deliverable={"description": "one file"},
    )
    return Contract(**{**base, **over})  # type: ignore[arg-type]


def test_the_body_has_a_goal_the_request_the_criteria_and_the_deliverable() -> None:
    assert body(contract(), {"topic": "ai"}, [], "") == (
        "## Goal\nDeliver the service `brief`: A brief.\n\n## Request\n- topic: ai\n\n## Acceptance criteria\n- C1: Short\n\n## Deliverable\none file"
    )


def test_the_inputs_follow_the_order_of_the_contract_and_only_those_given_are_listed() -> None:
    both = body(contract(), {"week": "10", "topic": "ai"}, [], "")
    assert "## Request\n- topic: ai\n- week: 10\n\n" in both
    assert "## Request\n- week: 10\n\n" in body(contract(), {"week": "10"}, [], "")


def test_a_value_of_several_lines_is_indented_under_its_item() -> None:
    assert "- topic: a\n  b\n  c\n" in body(contract(), {"topic": "a\nb\nc"}, [], "")


def test_without_inputs_it_says_so() -> None:
    assert "## Request\n(no inputs)\n\n" in body(contract(), {}, [], "")


def test_the_extra_criteria_come_after_the_contracts() -> None:
    assert "## Acceptance criteria\n- C1: Short\n- this request only: More\n- this request only: Even more\n\n" in body(contract(), {}, ["More", "Even more"], "")


def test_the_deliverable_lists_its_format_size_and_path_in_that_order() -> None:
    deliverable = {"description": "a report", "path": "/o.pdf", "max_words": 10, "format": "pdf"}
    assert body(contract(deliverable=deliverable), {}, [], "").endswith("## Deliverable\na report (format: pdf; at most 10 words; path: /o.pdf)")
    assert body(contract(deliverable={"description": "a report", "path": "/o.pdf"}), {}, [], "").endswith("a report (path: /o.pdf)")


def test_the_note_of_the_requester_comes_last_stripped_and_only_when_there_is_one() -> None:
    assert body(contract(), {}, [], "  Be quick.\n").endswith("## Deliverable\none file\n\n## Note from the requester\nBe quick.")
    assert "Note from the requester" not in body(contract(), {}, [], "   ")


def test_the_request_body_lists_contract_criteria_with_ids_and_extras_without() -> None:
    c = contract(acceptance=["B", "D"])
    history = number_criteria([(1, "root", ["A", "B", "C"]), (2, "root", ["B", "D"])])  # A and C were removed; B kept C2, D is C4
    text = BODIES.body(c, [x for x in history if x.current], {}, ["only now"], "")
    assert "## Acceptance criteria\n- C2: B\n- C4: D\n- this request only: only now\n\n## Deliverable" in text
    assert "C1" not in text and "C3" not in text
