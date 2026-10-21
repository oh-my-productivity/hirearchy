"""``ContractAmender``: what an amendment of a contract changes, and the note that tells the owner."""

from __future__ import annotations

import pytest

from hirearchy.kernel import OrgError
from hirearchy.services import Contract, Criterion, number_criteria
from hirearchy.services._amend import ContractAmender

A = ContractAmender()


IDS = {"one": "C1", "two": "C2", "three": "C3"}


def ided(*texts: str) -> list[Criterion]:  # the criteria of a contract that never changed: C1, C2, ...
    return number_criteria([(1, "root", list(texts))])


def contract(**over: object) -> Contract:
    base: dict[str, object] = dict(
        name="brief", owner="ceo", description="D", inputs=[{"name": "topic", "description": "t", "required": True}],
        acceptance=["one", "two"], deliverable={"description": "a file"}, budget=5, locked=False, version=1, defined_by="root", notes="",
    )
    return Contract(**{**base, **over})  # type: ignore[arg-type]


# ------------------------------------------------------------------------------ listed


def test_listed_renders_id_colon_text() -> None:
    many = number_criteria([(1, "root", ["a", "b"]), (2, "root", ["b", "c"])])
    assert A.listed(many) == "C1: a\nC2: b\nC3: c"
    assert A.listed(ided("a"), "  ") == "  C1: a" and A.listed([]) == ""


# ------------------------------------------------------------------------------ amended_criteria


def test_nothing_to_add_or_remove_keeps_the_criteria() -> None:
    assert A.amended_criteria("brief", ided("one", "two"), None, None) == ["one", "two"]


def test_criteria_are_removed_then_added_after_the_rest() -> None:
    assert A.amended_criteria("brief", ided("one", "two"), ["three"], ["one"]) == ["two", "three"]
    assert A.amended_criteria("brief", ided("one", "two"), "- x\n- y", None) == ["one", "two", "x", "y"]


def test_a_criterion_can_be_replaced_in_one_call_only_by_removing_and_adding_other_text() -> None:
    assert A.amended_criteria("brief", ided("one"), ["uno"], ["one"]) == ["uno"]


def test_the_refusals_list_the_current_criteria() -> None:
    listing = "Current criteria of `brief`:\nC1: one\nC2: two"
    with pytest.raises(OrgError) as e:
        A.amended_criteria("brief", ided("one", "two"), None, ["three", "four"])
    assert str(e.value) == f'remove_acceptance must be the exact text of existing criteria; not found: "three"; "four".\n{listing}'
    with pytest.raises(OrgError) as e:
        A.amended_criteria("brief", ided("one", "two"), ["two"], None)
    assert str(e.value) == (
        f'add_acceptance: already a criterion: "two". Add only new criteria (to reword one, remove it and add the new text in two calls).\n{listing}'
    )
    with pytest.raises(OrgError) as e:
        A.amended_criteria("brief", ided("one", "two"), ["x", "y", "x", "y"], None)
    assert str(e.value) == 'add_acceptance lists the same criterion twice: "x"; "y"'
    with pytest.raises(OrgError) as e:
        A.amended_criteria("brief", ided("one"), None, ["one"])
    assert str(e.value) == f"that would leave `brief` without acceptance criteria: a service needs at least one.\nCurrent criteria of `brief`:\nC1: one"


# ------------------------------------------------------------------------------ changes


def test_an_unchanged_contract_changes_nothing() -> None:
    assert A.changes(contract(), contract(version=2), IDS) == []


def test_every_kind_of_change_has_its_line() -> None:
    new = contract(
        acceptance=["two", "three"], inputs=[{"name": "week", "description": "w", "required": False}], budget=7, locked=True, description="E",
        deliverable={"description": "a pdf", "format": "pdf", "max_words": 9, "path": "/x.pdf"}, notes="N", version=2,
    )
    assert A.changes(contract(), new, IDS) == [
        "- acceptance removed: C1: one",
        "+ acceptance added: C3: three",
        "- input removed: topic*: t",
        "+ input added: week: w",
        "budget per request: 5 -> 7 runs",
        "locked: false -> true (you may no longer revise the playbook)",
        'description: "D" -> "E"',
        'deliverable: "a file" -> "a pdf" (format: pdf; max_words: 9; path: /x.pdf)',
        'notes: "" -> "N"',
    ]


def test_unlocking_does_not_say_the_owner_may_no_longer_revise() -> None:
    assert A.changes(contract(locked=True), contract(locked=False, version=2), IDS) == ["locked: true -> false"]


def test_only_a_new_order_is_a_change_of_its_own() -> None:
    assert A.changes(contract(), contract(acceptance=["two", "one"], version=2), IDS) == ["acceptance: order changed"]
    assert A.changes(contract(), contract(acceptance=["two", "one"], budget=6, version=2), IDS) == ["budget per request: 5 -> 6 runs"]


# ------------------------------------------------------------------------------ diff


def test_the_note_names_who_changed_what_and_where_to_read_it() -> None:
    text = A.diff(
        contract(), contract(version=2), ["budget per request: 5 -> 6 runs"], "ceo/services/brief/SERVICE.md", ided("one", "two"), frozenset(),
    )
    assert text == (
        "root changed the contract of service `brief` (v1 -> v2). Read it, and follow the new criteria from the next request on:\n"
        "budget per request: 5 -> 6 runs\nAcceptance criteria now:\nC1: one\nC2: two\nContract: ceo/services/brief/SERVICE.md"
    )


def test_a_contract_defined_by_nobody_is_changed_by_the_parent() -> None:
    assert A.diff(contract(defined_by=""), contract(version=2), [], "x", [], frozenset()).startswith("your parent changed the contract of service `brief`")


def test_the_note_marks_an_unconfirmed_amendment() -> None:
    criteria = number_criteria([(1, "root", ["one", "two"]), (2, "root", ["one", "two", "three", "four"]), (3, "ceo", ["one", "two", "three", "four", "five"])])
    new = contract(acceptance=["one", "two", "three", "four", "five"], version=3)
    nothing = A.diff(contract(), new, [], "x", criteria, frozenset())
    assert "Acceptance criteria now:\nC1: one\nC2: two\nC3: three (not confirmed)\nC4: four (not confirmed)\nC5: five\n" in nothing  # v1 and non-root: no mark
    some = A.diff(contract(), new, [], "x", criteria, ["C3"])
    assert "C3: three\nC4: four (not confirmed)\nC5: five\n" in some
    assert "(not confirmed)" not in A.diff(contract(), new, [], "x", criteria, {"C3", "C4"})
