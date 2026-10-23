"""Stable criterion ids ``C<k>``: derived from the order in which a criterion's exact text first appeared in the history of a contract
(``number_criteria``, pure), found again in a text list (``criteria_of``), and read from the stored versions (``stored_versions``)."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from pathlib import Path

import hirearchy.services as services
from hirearchy.services.testing import fs_world

from ._support import amend, define, populated, write_version


def numbered(*versions: tuple[int, str, list[str]], basis: Mapping[int, tuple[str, bool]] | None = None) -> list[services.Criterion]:
    return services.number_criteria(list(versions), basis)


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


def test_confirmed_amendments_needs_both() -> None:
    found = numbered((1, "root", ["A", "B"]), (2, "root", ["A", "B", "C", "D"]), (3, "root", ["A", "C", "D", "E"]))  # C1 A, C2 B, C3 C, C4 D, C5 E

    def ids_of(confirmed: Collection[str]) -> list[str]:
        return [c.id for c in services.confirmed_amendments(found, confirmed)]

    assert ids_of({"C5", "C3", "C4"}) == ["C3", "C4", "C5"]  # amended and confirmed, in the order given
    assert ids_of({"C4"}) == ["C4"]  # of three amendments, only the confirmed one
    assert ids_of(set()) == [] and ids_of(()) == []  # amended only: out
    assert ids_of({"C1"}) == []  # a confirmed v1 criterion is no amendment
    assert ids_of({"C2"}) == []  # a removed criterion is out, confirmed or not
    assert ids_of({"C9"}) == [] and services.confirmed_amendments([], {"C1"}) == []  # an id the contract never had; an empty contract


def test_number_criteria_carries_the_basis_of_the_version_that_added_a_text() -> None:
    found = numbered(
        (1, "root", ["A", "B"]), (2, "root", ["A", "B", "C"]), (3, "root", ["A", "B", "C", "D"]), (4, "root", ["A", "C", "D"]), (5, "root", ["A", "C", "D", "B"]),
        basis={2: ("N2", False), 3: ("", True), 4: ("N4", False), 5: ("N5", False)},
    )
    assert {c.text: (c.answers, c.user) for c in found} == {
        "A": ("", False),  # in v1: no basis
        "B": ("N5", False),  # in v1, removed in v4, added again in v5: the latest version that added it
        "C": ("N2", False),  # added by v2 and kept by v3, v4, v5: the basis of v2, not of the later versions
        "D": ("", True),  # added by v3, user-initiated
    }
    assert [c.since for c in found] == [1, 1, 2, 3]  # the basis does not move `since`


def test_v1_texts_have_no_basis() -> None:
    found = numbered((1, "root", ["A", "B"]), basis={1: ("N1", True)})
    assert [(c.answers, c.user) for c in found] == [("", False), ("", False)]
    assert all(c.answers == "" and not c.user for c in numbered((1, "root", ["A"])))  # no basis at all: the default


def test_a_text_added_by_a_version_without_a_basis_has_none() -> None:
    found = numbered((1, "root", ["A"]), (2, "ceo", ["A", "B"]), basis={3: ("N3", False)})
    assert [(c.answers, c.user) for c in found] == [("", False), ("", False)]  # a legacy version, an agent's version


def test_stored_basis_reads_the_map_from_stored_versions(tmp_path: Path) -> None:
    from hirearchy.services._criteria import stored_basis

    w = populated(fs_world(tmp_path))
    define(w, acceptance=["A", "B"])
    assert stored_basis(w.store, "ceo", "weekly-brief") == {1: ("", False)}
    write_version(w, 2, ["A", "B", "C"], answers="20261018T100000000012-root-0004", about="C1", words="Yes, add it.")
    write_version(w, 3, ["A", "B", "C", "D"], initiated="user", words="Add D.")
    write_version(w, 4, ["A", "B", "C", "D", "E"])
    assert stored_basis(w.store, "ceo", "weekly-brief") == {
        1: ("", False), 2: ("20261018T100000000012-root-0004", False), 3: ("", True), 4: ("", False),
    }
    assert stored_basis(w.store, "ceo", "no-such-service") == {}


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
