"""``as_int``, ``as_time``, ``contract_of``, ``playbook_of``: the contract and the playbook as values, with the defaults of a damaged file."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy.kernel import JsonObject
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
