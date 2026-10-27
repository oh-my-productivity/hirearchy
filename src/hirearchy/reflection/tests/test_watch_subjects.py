"""The facts the watch reads (design 3, 8.1): the subjects of a rejection, the lineage of a criterion as of a time (B3, B4), coverage and refs."""

from __future__ import annotations

from hirearchy.kernel import ROOT, Message
from hirearchy.reflection._watch import (
    EPOCH, coverage_of, defined_moment, lineage_as_of, moment_of, pending_rejection, refs_of, subjects_of, until,
)
from hirearchy.services import Contract, Criterion

from ._watch_kit import Mailbag, contract, records, stamp

V1 = ["a", "b", "c", "d"]  # C1, C2, C3, C4
NINE = ["w", "x", "y", "z", "u", "v", "q", "r", "s"]  # C1-C9: "v" is C6
TEN = [*NINE[:5], "ten", *NINE[6:]]  # C6 replaced by C10


def one_rejection(bag: Mailbag, name: str = "c1", tick: int = 1) -> Message:
    """A request, its delivery and the user's rejection of it; returns the rejection's note."""
    task = bag.ask(name, tick)
    bag.answer(task, tick + 1)
    return bag.verdict(task, tick + 2, "reject")


def test_subjects_are_the_rejection_its_human_link_and_its_answering_versions_about_answer_and_removed_ids() -> None:
    bag = Mailbag()
    note = one_rejection(bag)
    bag.link(note, 5, "C2")  # the user's yes: what the rejection is about
    v2 = contract(2, ["a", "b", "c", "e"], 4, answers=note.id, about="C3")  # removes d (C4), adds e (C5)
    found = records(bag, contract(1, V1, 0), v2)
    # R1 itself; C2 (the link); C3 (the question's id); C5 (what the version adds); C4 (what it removes, and C5's lineage)
    assert subjects_of(found, "R1") == frozenset({"R1", "C2", "C3", "C4", "C5"})


def test_a_failed_link_write_changes_no_subject() -> None:
    """The answering version alone relates the rejection: the link note it would have written (its added ids) adds nothing."""
    bag = Mailbag()
    note = one_rejection(bag)
    v2 = contract(2, ["a", "b", "c", "e"], 4, answers=note.id, about="C3")
    without = records(bag, contract(1, V1, 0), v2)
    bag.link(note, 5, "C5")  # the link the product would have written: the ids the version adds
    with_link = records(bag, contract(1, V1, 0), v2)
    assert not pending_rejection(without, "R1")
    assert subjects_of(without, "R1") == frozenset({"R1", "C3", "C4", "C5"})
    assert subjects_of(with_link, "R1") == subjects_of(without, "R1")


def test_a_rejection_without_an_answer_is_pending_with_itself_as_subject() -> None:
    bag = Mailbag()
    one_rejection(bag)
    found = records(bag, contract(1, V1, 0))
    assert pending_rejection(found, "R1")
    assert subjects_of(found, "R1") == frozenset({"R1"})


def test_same_as_an_unanswered_rejection_is_pending_until_it_is_answered() -> None:
    """Row xviii's subjects: R2 linked "same as R1" has no subject beyond itself while R1 has no answer."""
    bag = Mailbag()
    first = one_rejection(bag, "c1", 1)
    second = bag.ask("c2", 10)
    bag.answer(second, 11)
    bag.link(bag.verdict(second, 12, "reject"), 13, "R1")
    early = records(bag, contract(1, V1, 0))
    assert pending_rejection(early, "R1") and pending_rejection(early, "R2")
    assert subjects_of(early, "R2") == frozenset({"R2"})
    bag.link(first, 14, "C2")  # R1 is answered: "same as R1" now resolves through its link
    late = records(bag, contract(1, V1, 0))
    assert not pending_rejection(late, "R1") and not pending_rejection(late, "R2")
    assert subjects_of(late, "R2") == frozenset({"R2", "R1", "C2"})


def test_a_lineage_holds_what_the_adding_answer_removed() -> None:
    """D10: an answer to one question is one change, so what it removed is what it replaced."""
    versions = [contract(1, ["a", "b"], 0), contract(2, ["a", "x"], 10, answers="n1")]  # C1 a, C2 b, C3 x: v2 removes b
    assert lineage_as_of(versions, "C3", stamp(20)) == ("C2",)
    assert lineage_as_of(versions, "C3", stamp(5)) == ()  # as of before v2 was defined, C3 did not exist
    assert lineage_as_of(versions, "C1", stamp(20)) == ()  # a v1 criterion never removed and re-added has none


def test_a_v1_text_removed_then_re_added_has_the_lineage_of_the_re_adding_answer() -> None:
    """Row xxiii (B4): C6 (a v1 text) is removed by one answer (adding C10) and re-added by its exact text by a later one (removing C10)."""
    versions = [
        contract(1, NINE, 0),
        contract(2, TEN, 10, answers="n1"),  # removes C6, adds C10
        contract(3, NINE, 20, answers="n2"),  # re-adds C6 by its exact text, removes C10
    ]
    assert lineage_as_of(versions, "C6", stamp(25)) == ("C10",)
    assert lineage_as_of(versions, "C10", stamp(25)) == ("C6",)  # each id once: C10's own lineage is C6, whose lineage is C10 again
    assert lineage_as_of(versions, "C6", stamp(15)) == ()  # before the re-add: C6 had no lineage
    bag = Mailbag()
    bag.link(one_rejection(bag), 25, "C6")  # a rejection answered about C6 after the re-add
    assert subjects_of(records(bag, *versions), "R1") == frozenset({"R1", "C6", "C10"})  # relates to a rule that cited C10


def test_a_rejection_answered_before_the_re_add_keeps_its_subjects() -> None:
    """Row xxiv (B4): the subjects of a rejection are taken at the time of its answer."""
    bag = Mailbag()
    bag.link(one_rejection(bag), 6, "C6")  # answered about C6 while C6 had no lineage
    versions = [contract(1, NINE, 0), contract(2, TEN, 10, answers="n1"), contract(3, NINE, 20, answers="n2")]
    assert subjects_of(records(bag, *versions), "R1") == frozenset({"R1", "C6"})  # the later re-add does not bring C10 in


def test_a_lineage_cycle_ends_with_each_id_once() -> None:
    """Row xxv (B4): C6 -> C10 -> C6 -> C10 over three answers."""
    versions = [
        contract(1, NINE, 0),
        contract(2, TEN, 10, answers="n1"),  # removes C6, adds C10
        contract(3, NINE, 20, answers="n2"),  # removes C10, re-adds C6
        contract(4, TEN, 30, answers="n3"),  # removes C6, re-adds C10
    ]
    assert lineage_as_of(versions, "C10", stamp(35)) == ("C6",)
    assert lineage_as_of(versions, "C6", stamp(25)) == ("C10",)


def test_a_user_initiated_criterion_has_no_lineage() -> None:
    versions = [contract(1, ["a", "b"], 0), contract(2, ["a", "x"], 10, initiated="user")]
    assert lineage_as_of(versions, "C3", stamp(20)) == ()


def test_a_contract_versions_time_is_its_defined_never_the_contracts_created() -> None:
    """B3: every version carries the contract's ``created`` from v1; only ``defined`` says when a version was written."""
    late = contract(2, ["a", "b"], 50, created=stamp(1))
    assert defined_moment(late)[0] == stamp(50)
    assert defined_moment(Contract(name="x", owner=ROOT))[0] == EPOCH  # a version that says no time
    bag = Mailbag()
    one_rejection(bag)
    found = records(bag, contract(1, V1, 0), late)
    assert [c.version for c in until(found, (stamp(10), 1, "")).contracts] == [1]  # v2 is not there at tick 10, whatever its created says
    assert [c.version for c in until(found, (stamp(60), 1, "")).contracts] == [1, 2]


def test_at_an_equal_microsecond_a_version_comes_before_its_link_note() -> None:
    """B3: ``define_service`` writes the contract version, then the link note; at one microsecond the version sorts first."""
    bag = Mailbag()
    note = one_rejection(bag)
    link = bag.link(note, 7, "C5", us=4)
    version = contract(2, ["a", "b", "c", "e"], 7, answers=note.id, us=4)  # defined at the very microsecond of the link note
    assert stamp(7, 4) == version.defined
    assert defined_moment(version) < moment_of(link)
    found = records(bag, contract(1, V1, 0), version)
    at_version = until(found, defined_moment(version))
    assert [c.version for c in at_version.contracts] == [1, 2]  # the version is in ...
    assert at_version.assertions[0].about == ()  # ... and the link note, which comes after it, is not
    assert found.assertions[0].about == ("C5",)


def test_coverage_is_current_criteria_and_confirmed_assertions_about_a_current_or_no_criterion() -> None:
    bag = Mailbag()
    notes = [one_rejection(bag, f"c{i}", 10 * i) for i in range(1, 6)]
    bag.link(notes[0], 100, "C1")  # R1: confirmed, about a current criterion
    bag.link(notes[1], 101, "C2")  # R2: confirmed, about a removed criterion only
    bag.link(notes[2], 102, "none")  # R3: no lasting rule
    bag.link(notes[3], 103, "R3")  # R4: "same as R3", which is about nothing: R4 stays about an R id, no criterion at all
    # R5 has no human link
    found = records(bag, contract(1, ["a", "b"], 0))
    criteria = [Criterion("C1", "a", 1, ROOT, True), Criterion("C2", "b", 1, ROOT, False)]
    refs = frozenset({"C1", "C2", "R1", "R2", "R3", "R4", "R5", "R9"})
    assert coverage_of(refs, criteria, found.assertions) == ("R1", "R4", "C1")
    assert coverage_of(frozenset({"C2", "R2"}), criteria, found.assertions) == ()  # the client lowered that bar herself


def test_refs_are_taken_as_of_a_texts_live_from() -> None:
    """``C<k>``/``R<k>`` tokens of a text, plus the criteria each ``R`` was about when the text went live; a later link changes none."""
    bag = Mailbag()
    note = one_rejection(bag)
    bag.link(note, 10, "C6")
    bag.link(note, 50, "C7")  # a corrected link, recorded after the text went live
    found = records(bag, contract(1, V1, 0))
    text = "Check c9 and the date (R1)."
    assert refs_of(found, text, (), stamp(20)) == frozenset({"C9", "R1", "C6"})
    assert refs_of(found, text, (), stamp(5)) == frozenset({"C9", "R1"})  # before any link: R1 was about nothing yet
    assert refs_of(found, text, (), stamp(60)) == frozenset({"C9", "R1", "C7"})  # the corrected link is the effective one from tick 50
    assert refs_of(found, "No ids here.", ("R1", "C3"), stamp(20)) == frozenset({"R1", "C3", "C6"})  # a gated item's refs are its why entry
