"""Stable criterion ids ``C<k>``: derived from the order in which a criterion's exact text first appeared in the history of a contract
(``number_criteria``, pure), found again in a text list (``criteria_of``), and read from the stored versions (``stored_versions``)."""

from __future__ import annotations

from pathlib import Path

import hirearchy.services as services
from hirearchy.services.testing import fs_world

from ._support import amend, define, populated


def numbered(*versions: tuple[int, str, list[str]]) -> list[services.Criterion]:
    return services.number_criteria(list(versions))


def ids(criteria: list[services.Criterion]) -> dict[str, str]:
    return {c.text: c.id for c in criteria}


def test_v1_criteria_are_numbered_in_list_order() -> None:
    found = numbered((1, "root", ["A", "B", "C"]))
    assert [(c.id, c.text, c.since, c.by, c.current) for c in found] == [
        ("C1", "A", 1, "root", True), ("C2", "B", 1, "root", True), ("C3", "C", 1, "root", True),
    ]


def test_an_amendment_appends_the_next_free_id() -> None:
    found = numbered((1, "root", ["A", "B"]), (2, "root", ["A", "B", "C"]))
    assert ids(found) == {"A": "C1", "B": "C2", "C": "C3"}
    assert [(c.since, c.by) for c in found] == [(1, "root"), (1, "root"), (2, "root")]


def test_removing_a_criterion_never_renumbers_the_others_or_reuses_its_id() -> None:
    found = numbered((1, "root", ["A", "B", "C"]), (2, "root", ["A", "C"]), (3, "root", ["A", "C", "D"]))
    assert ids(found) == {"A": "C1", "B": "C2", "C": "C3", "D": "C4"}
    assert {c.id: c.current for c in found} == {"C1": True, "C2": False, "C3": True, "C4": True}


def test_a_reworded_criterion_is_new() -> None:
    found = numbered((1, "root", ["A", "B"]), (2, "root", ["A", "B, in full"]))
    assert ids(found) == {"A": "C1", "B": "C2", "B, in full": "C3"}
    assert {c.id: c.current for c in found} == {"C1": True, "C2": False, "C3": True}


def test_an_identical_text_added_again_keeps_its_id() -> None:
    found = numbered((1, "root", ["A", "B"]), (2, "root", ["A"]), (3, "root", ["A", "B"]))
    assert ids(found) == {"A": "C1", "B": "C2"}
    again = next(c for c in found if c.id == "C2")
    assert (again.since, again.current, again.amended) == (1, True, False)  # it was in the contract from the start


def test_a_full_replacement_keeps_the_ids_of_kept_texts() -> None:
    found = numbered((1, "root", ["A", "B", "C"]), (2, "root", ["C", "X", "A"]))
    assert ids(found) == {"A": "C1", "B": "C2", "C": "C3", "X": "C4"}
    assert {c.id: c.current for c in found} == {"C1": True, "C2": False, "C3": True, "C4": True}


def test_amended_only_from_v2_defined_by_root_and_current() -> None:
    found = numbered((1, "root", ["A"]), (2, "root", ["A", "B"]), (3, "root", ["A", "C"]))
    assert {c.text: c.amended for c in found} == {"A": False, "B": False, "C": True}  # A: since v1; B: removed again; C: added by root in v3


def test_a_version_defined_by_an_agent_is_not_amended() -> None:
    found = numbered((1, "root", ["A"]), (2, "ceo", ["A", "B"]), (3, "", ["A", "B", "C"]))
    assert {c.text: c.amended for c in found} == {"A": False, "B": False, "C": False}


def test_criteria_of_follows_the_order_of_texts_and_skips_unknown() -> None:
    found = numbered((1, "root", ["A", "B", "C"]), (2, "root", ["A", "C", "D"]))
    assert [c.id for c in services.criteria_of(found, ["D", "nothing like it", "A"])] == ["C4", "C1"]
    assert services.criteria_of(found, []) == []


def test_missing_history_files_are_skipped(tmp_path: Path) -> None:
    from hirearchy.services._criteria import stored_versions

    w = populated(fs_world(tmp_path))
    define(w, acceptance=["A", "B"])
    amend(w, add_acceptance=["C"])
    amend(w, add_acceptance=["D"], remove_acceptance=["B"])
    assert stored_versions(w.store, "ceo", "weekly-brief") == [(1, "root", ["A", "B"]), (2, "root", ["A", "B", "C"]), (3, "root", ["A", "C", "D"])]
    (tmp_path / "ceo/services/weekly-brief/history/SERVICE.v2.md").unlink()
    versions = stored_versions(w.store, "ceo", "weekly-brief")
    assert versions == [(1, "root", ["A", "B"]), (3, "root", ["A", "C", "D"])]
    assert ids(services.number_criteria(versions)) == {"A": "C1", "B": "C2", "C": "C3", "D": "C4"}
