"""``as_int``, ``as_time``, ``contract_of``, ``playbook_of``: the contract and the playbook as values, with the defaults of a damaged file."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy.kernel import JsonObject
from hirearchy.services import PlaybookItem, PlaybookSection
from hirearchy.services._parse import as_int, as_time, contract_of, playbook_of


@pytest.mark.parametrize("value, default, expected", [
    (None, 0, 0), (None, 7, 7), (True, 3, 3), (False, 3, 3), (5, 0, 5), ("12", 0, 12), (" 7 ", 0, 7), ("x", 4, 4), (2.9, 0, 2), ([1], 9, 9),
    ({"a": 1}, 9, 9), (datetime(2026, 1, 1), 5, 5),
])
def test_a_whole_number_or_the_default(value: object, default: int, expected: int) -> None:
    assert as_int(value, default) == expected


def test_a_time_is_parsed_and_made_aware() -> None:
    assert as_time("2026-01-02T03:04:05+00:00") == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert as_time("2026-01-02T03:04:05") == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert as_time(datetime(2026, 1, 2)) == datetime(2026, 1, 2, tzinfo=timezone.utc)


@pytest.mark.parametrize("value", [None, "", 0, "not a time"])
def test_no_time_when_it_is_empty_or_unreadable(value: object) -> None:
    assert as_time(value) is None


def test_a_contract_is_read_from_its_frontmatter(tmp_path: Path) -> None:
    meta: JsonObject = {
        "description": "D", "inputs": [{"name": "topic", "description": "t", "required": True}, {"name": "w"}, {"description": "no name"}, "text"],
        "acceptance": ["a", 2], "deliverable": {"description": "x"}, "budget": 4, "locked": True, "version": 3, "defined_by": "root",
        "defined": "2026-01-02T00:00:00+00:00", "created": "2026-01-01T00:00:00+00:00",
    }
    path = tmp_path / "SERVICE.md"
    c = contract_of("ceo", "brief", meta, "\n Notes. \n", path)
    assert (c.name, c.owner, c.description, c.budget, c.locked, c.version, c.defined_by, c.notes, c.path) == (
        "brief", "ceo", "D", 4, True, 3, "root", "Notes.", path,
    )
    assert c.inputs == [{"name": "topic", "description": "t", "required": True}, {"name": "w", "description": "", "required": True}]
    assert c.acceptance == ["a", "2"] and c.deliverable == {"description": "x"}
    assert c.defined == datetime(2026, 1, 2, tzinfo=timezone.utc) and c.created == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_contract_of_reads_answers_about_words_and_initiated() -> None:
    answered = contract_of("ceo", "b", {"version": 2, "answers": "20261018T100000000012-root-0004", "about": "C2", "words": "Yes, add it."}, "", None)
    assert (answered.answers, answered.about, answered.words, answered.initiated) == ("20261018T100000000012-root-0004", "C2", "Yes, add it.", "")
    own = contract_of("ceo", "b", {"version": 2, "initiated": "user", "words": "Keep it to one page."}, "", None)
    assert (own.answers, own.about, own.words, own.initiated) == ("", "", "Keep it to one page.", "user")
    odd = contract_of("ceo", "b", {"answers": 7, "about": None, "words": ["x"], "initiated": False}, "", None)
    assert (odd.answers, odd.about, odd.initiated) == ("7", "", "")  # text, or nothing for what is none


def test_a_legacy_version_has_no_basis() -> None:
    legacy = contract_of("ceo", "b", {"version": 3, "defined_by": "root", "acceptance": ["a"]}, "", None)
    assert (legacy.answers, legacy.about, legacy.words, legacy.initiated) == ("", "", "", "")


def test_a_required_input_is_required_unless_it_says_false() -> None:
    c = contract_of("ceo", "b", {"inputs": [{"name": "a", "required": False}, {"name": "b", "required": 0}, {"name": "c", "required": None}]}, "", None)
    assert [i["required"] for i in c.inputs] == [False, True, True]


def test_a_contract_without_fields_has_the_defaults() -> None:
    c = contract_of("ceo", "brief", {}, "", None)
    assert (c.description, c.inputs, c.acceptance, c.deliverable, c.budget, c.locked, c.version, c.defined_by, c.defined, c.created, c.notes, c.path) == (
        "", [], [], {}, 1, False, 1, "", None, None, "", None,
    )


def test_the_budget_and_the_version_are_at_least_one() -> None:
    c = contract_of("ceo", "b", {"budget": 0, "version": -2}, "", None)
    assert (c.budget, c.version) == (1, 1)
    c = contract_of("ceo", "b", {"budget": "9", "version": "2"}, "", None)
    assert (c.budget, c.version) == (9, 2)


def test_locked_is_true_only_for_true() -> None:
    assert not contract_of("ceo", "b", {"locked": "true"}, "", None).locked
    assert not contract_of("ceo", "b", {"locked": 1}, "", None).locked


def test_the_creation_time_falls_back_on_the_definition_time() -> None:
    c = contract_of("ceo", "b", {"defined": "2026-01-02T00:00:00+00:00"}, "", None)
    assert c.created == c.defined and c.created is not None


def test_a_deliverable_that_is_not_a_mapping_is_empty() -> None:
    assert contract_of("ceo", "b", {"deliverable": "a file"}, "", None).deliverable == {}


def test_a_playbook_is_read_from_its_frontmatter(tmp_path: Path) -> None:
    path = tmp_path / "PLAYBOOK.md"
    pb = playbook_of({"version": 2, "revised": "2026-01-02T00:00:00+00:00", "by": "ceo", "reason": "why"}, "\n Steps. \n", path)
    assert (pb.version, pb.by, pb.reason, pb.body, pb.path) == (2, "ceo", "why", "Steps.", path)
    assert pb.revised == datetime(2026, 1, 2, tzinfo=timezone.utc)


def test_a_playbook_without_fields_is_version_zero() -> None:
    pb = playbook_of({}, "", None)
    assert (pb.version, pb.revised, pb.by, pb.reason, pb.body, pb.path) == (0, None, "", "", "", None)


def test_a_legacy_playbook_reads_evidence_empty_and_admitted_blank() -> None:
    legacy = playbook_of({"version": 2, "by": "ceo", "reason": "r"}, "Steps.", None)
    assert (legacy.evidence, legacy.admitted) == ([], "")


def test_the_evidence_and_the_rule_that_admitted_a_playbook_are_read() -> None:
    pb = playbook_of({"version": 3, "evidence": ["R1", 2, " C3 ", ""], "admitted": "b", "restores": 1}, "Steps.", None)
    assert (pb.evidence, pb.admitted) == (["R1", "2", "C3"], "b")
    assert playbook_of({"evidence": "R1", "admitted": None}, "", None).evidence == []  # a damaged file reads as no evidence


ITEM_BODY = (
    "## Steps\n1. [P1] Read the request.\n2. [P12] Compare every date. (WHY R2, R3; C6)\n\n## Rules\n"
    "- [P13] WHEN a date is relative THEN convert it. WHY R2, R3; C6"
)
ITEM_META: JsonObject = {
    "version": 4, "revised": "2026-01-02T00:00:00+00:00", "by": "ceo", "reason": "why", "evidence": ["R2", "R3", "C6"], "admitted": "b",
    "items_max": 13, "rules": ["P13"], "why": {"P12": ["R2", "R3", "C6"], "P13": ["R2", "R3", "C6"]}, "op": "add", "item": "P13",
    "related": ["R4"], "acknowledged": "20261018T100000000012-root-0004",
}


def test_playbook_of_fills_items_sections_and_the_item_keys() -> None:
    pb = playbook_of(ITEM_META, "\n" + ITEM_BODY + "\n", None)
    assert pb.parse_error == "" and pb.version == 4 and pb.body == ITEM_BODY
    assert pb.items == (
        PlaybookItem("P1", "step", "## Steps", "Read the request."),
        PlaybookItem("P12", "step", "## Steps", "Compare every date.", "", ("R2", "R3", "C6")),
        PlaybookItem("P13", "rule", "## Rules", "convert it.", "a date is relative", ("R2", "R3", "C6")),
    )
    assert pb.sections == (PlaybookSection("## Steps", True, ("P1", "P12")), PlaybookSection("## Rules", False, ("P13",)))
    assert (pb.items_max, pb.rules, pb.op, pb.item, pb.related, pb.acknowledged) == (
        13, ("P13",), "add", "P13", ("R4",), "20261018T100000000012-root-0004",
    )
    assert pb.why == {"P12": ("R2", "R3", "C6"), "P13": ("R2", "R3", "C6")}
    assert pb.evidence == ["R2", "R3", "C6"] and pb.admitted == "b"


def test_a_body_without_items_max_is_legacy_with_items_none() -> None:
    pb = playbook_of({"version": 2}, "## Steps\n1. [P1] words that look like an item", None)
    assert pb.items is None and pb.sections == () and pb.parse_error == ""
    assert (pb.items_max, pb.rules, pb.why, pb.op, pb.item, pb.related, pb.acknowledged) == (0, (), {}, "", "", (), "")
    assert pb.body == "## Steps\n1. [P1] words that look like an item"


def test_an_item_file_without_items_is_not_legacy() -> None:
    pb = playbook_of({"version": 3, "items_max": 2, "rules": [], "why": {}, "op": "retire", "item": "P2"}, "## Steps", None)
    assert (pb.items, pb.parse_error, pb.items_max) == ((), "", 2)
    assert playbook_of({"version": 3, "items_max": 0}, "", None).items == ()


def test_an_item_body_that_does_not_parse_fills_parse_error_and_never_raises() -> None:
    pb = playbook_of({**ITEM_META, "items_max": 2}, "## Steps\n1. [P1] fine\nstray line", None)
    assert pb.items is None and pb.sections == () and pb.parse_error.startswith("line 3: ")
    assert pb.items_max == 2 and pb.version == 4 and pb.body == "## Steps\n1. [P1] fine\nstray line"  # the other fields are still read
    odd = playbook_of({"version": 1, "items_max": "x", "rules": "P1", "why": ["R1"], "related": 5, "op": None}, "## Steps\n- [P1] a", None)
    assert odd.parse_error == "" and odd.items_max == 0 and odd.rules == () and odd.why == {} and odd.related == () and odd.op == ""
    assert [i.id for i in odd.items or ()] == ["P1"]
