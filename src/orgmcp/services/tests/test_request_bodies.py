"""``TextRequestBodies``: the body of a request, as markdown."""

from __future__ import annotations

from orgmcp.services import Contract
from orgmcp.services._request import TextRequestBodies

BODIES = TextRequestBodies()


def contract(**over: object) -> Contract:
    base: dict[str, object] = dict(
        name="brief", owner="ceo", description="A brief.", inputs=[{"name": "topic", "description": "t", "required": True}, {"name": "week", "description": "", "required": False}],
        acceptance=["Short"], deliverable={"description": "one file"},
    )
    return Contract(**{**base, **over})  # type: ignore[arg-type]


def test_the_body_has_a_goal_the_request_the_criteria_and_the_deliverable() -> None:
    assert BODIES.body(contract(), {"topic": "ai"}, [], "") == (
        "## Goal\nDeliver the service `brief`: A brief.\n\n## Request\n- topic: ai\n\n## Acceptance criteria\n- Short\n\n## Deliverable\none file"
    )


def test_the_inputs_follow_the_order_of_the_contract_and_only_those_given_are_listed() -> None:
    body = BODIES.body(contract(), {"week": "10", "topic": "ai"}, [], "")
    assert "## Request\n- topic: ai\n- week: 10\n\n" in body
    assert "## Request\n- week: 10\n\n" in BODIES.body(contract(), {"week": "10"}, [], "")


def test_a_value_of_several_lines_is_indented_under_its_item() -> None:
    assert "- topic: a\n  b\n  c\n" in BODIES.body(contract(), {"topic": "a\nb\nc"}, [], "")


def test_without_inputs_it_says_so() -> None:
    assert "## Request\n(no inputs)\n\n" in BODIES.body(contract(), {}, [], "")


def test_the_extra_criteria_come_after_the_contracts() -> None:
    assert "## Acceptance criteria\n- Short\n- More\n- Even more\n\n" in BODIES.body(contract(), {}, ["More", "Even more"], "")


def test_the_deliverable_lists_its_format_size_and_path_in_that_order() -> None:
    deliverable = {"description": "a report", "path": "/o.pdf", "max_words": 10, "format": "pdf"}
    assert BODIES.body(contract(deliverable=deliverable), {}, [], "").endswith("## Deliverable\na report (format: pdf; at most 10 words; path: /o.pdf)")
    assert BODIES.body(contract(deliverable={"description": "a report", "path": "/o.pdf"}), {}, [], "").endswith("a report (path: /o.pdf)")


def test_the_note_of_the_requester_comes_last_stripped_and_only_when_there_is_one() -> None:
    assert BODIES.body(contract(), {}, [], "  Be quick.\n").endswith("## Deliverable\none file\n\n## Note from the requester\nBe quick.")
    assert "Note from the requester" not in BODIES.body(contract(), {}, [], "   ")
