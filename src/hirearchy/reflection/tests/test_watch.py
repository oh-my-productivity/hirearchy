"""``watch_states`` (design 8.1, 8.2, 8.7): the state of every playbook item, derived from the versions, the cases and their results, the criteria
and the contract versions. Rows i-xxv of 8.1 and the zero and empty cases of 8.7 each have a test named after them.

World: the playbook's P2 is a rule admitted at tick 10 on R1 (case c0's rejection, answered about C5); k is 3; a request is ``w.case(name, ask,
done, verdict=(tick, kind), link=(tick, ids))``. A rejection is related to P2 when it is answered about C5 (or R1)."""

from __future__ import annotations

from hirearchy.kernel import Message
from hirearchy.reflection._watch import watch_states
from hirearchy.services import ItemWatch, Playbook

from ._watch_kit import Watching, contract, playbook, rule, step


def setup() -> Watching:
    w = Watching()
    w.contracts.append(contract(1, ["a", "b", "c", "d", "e", "f"], 0))  # C1-C6: C5 is "e"
    first = [step("P1", "Read the request.")]
    w.versions.append(playbook(1, 0, first, op="first", admitted="first"))
    w.case("c0", 1, 2, verdict=(3, "reject"), link=(4, ["C5"]))  # R1: the rejection P2 rests on, answered about C5
    rule2 = rule("P2", "a date is relative", "convert it from the date of the request", why=("R1", "C5"))
    w.versions.append(playbook(2, 10, [*first, rule2], op="add", item="P2", admitted="c"))
    return w


def p2(w: Watching) -> ItemWatch:
    return w.states()["P2"]


def accepted(w: Watching, n: int = 3, first: int = 20) -> None:
    """``n`` candidates delivered and accepted in turn (c1: ask 20, done 21, accept 30; c2: 22, 23, 31 ...)."""
    for i in range(1, n + 1):
        w.case(f"c{i}", first + 2 * (i - 1), first + 2 * (i - 1) + 1, verdict=(30 + i - 1, "accept"))


# ----------------------------------------------------------------------------------------------------------------- 8.1 rows i-viii


def test_row_i_a_candidate_delivered_before_the_kth_and_judged_after_it_related_is_warning_never_kept() -> None:
    w = setup()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(34, "reject"))  # delivered before c3, judged after it
    w.case("c3", 24, 25, verdict=(32, "accept"))
    waiting = p2(w)
    assert (waiting.state, waiting.pending, waiting.related) == ("new", ("R2",), ())  # the answer is due: not kept, not warned yet
    w.bag.link(w.notes["c2"], 35, "C5")
    warned = p2(w)
    assert (warned.state, warned.related, warned.pending, warned.clean, warned.waiting) == ("warning", ("R2",), (), 2, 0)


def test_row_ii_the_same_candidate_unjudged_is_new_and_waiting_until_its_verdict() -> None:
    w = setup()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "accept"))
    c3 = w.case("c3", 24, 25)
    held = p2(w)
    assert (held.state, held.waiting, held.clean, held.k) == ("new", 1, 2, 3)
    w.bag.verdict(c3, 40, "accept")
    assert (p2(w).state, p2(w).waiting, p2(w).clean) == ("kept", 0, 3)


def test_row_iii_a_related_rejection_after_e_and_recorded_after_d_is_outside_the_window() -> None:
    w = setup()
    accepted(w)  # E is c3's delivery (25), D is c3's verdict (32)
    w.case("c4", 40, 41, verdict=(42, "reject"), link=(43, ["C5"]))  # a result after E, recorded after D
    kept = p2(w)
    assert (kept.state, kept.related, kept.clean) == ("kept", (), 3)


def test_row_iv_a_related_rejection_on_a_blocked_result_before_e_is_related() -> None:
    w = setup()
    accepted(w)
    w.case("cb", 19, 20, status="blocked", verdict=(28, "reject"), link=(29, ["C5"]))  # a blocked result is no delivery, but a file from it can be rejected
    warned = p2(w)
    assert (warned.state, warned.related, warned.clean) == ("warning", ("R2",), 3)  # cb is no candidate: c1-c3 are clean


def test_row_v_a_first_delivery_superseded_by_a_human_rework_the_user_accepts_is_clean() -> None:
    w = setup()
    c1 = w.case("c1", 20, 21)  # delivered, superseded before any verdict
    w.case("c1b", 22, 23, verdict=(33, "accept"), revises=c1, asked_by="human")
    w.case("c2", 24, 25, verdict=(30, "accept"))
    w.case("c3", 26, 27, verdict=(31, "accept"))
    kept = p2(w)
    assert (kept.state, kept.clean, kept.waiting) == ("kept", 3, 0)  # judged(c1) is the rework


def test_row_vi_a_relayed_rework_the_user_rejects_about_the_items_refs_is_related() -> None:
    w = setup()
    c1 = w.case("c1", 20, 21)
    w.case("c1b", 22, 23, verdict=(33, "reject"), link=(34, ["C5"]), revises=c1, asked_by="relayed")
    w.case("c2", 24, 25, verdict=(30, "accept"))
    w.case("c3", 26, 27, verdict=(31, "accept"))
    warned = p2(w)
    assert (warned.state, warned.related, warned.clean) == ("warning", ("R2",), 2)


def test_row_vii_the_kth_candidates_rework_rejected_about_the_item_is_related_inside_the_window() -> None:
    w = setup()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "accept"))
    c3 = w.case("c3", 24, 25)  # its first delivery is superseded by a rework
    w.case("c3b", 26, 29, verdict=(40, "reject"), link=(41, ["C5"]), revises=c3, asked_by="relayed")  # E is 29, D is the rejection's note
    warned = p2(w)
    assert (warned.state, warned.related, warned.waiting) == ("warning", ("R2",), 0)


def test_row_viii_a_late_verdict_on_the_superseded_first_delivery_leaves_judged_e_and_d_and_is_related_before_k() -> None:
    w = setup()
    w.case("c1", 20, 21, verdict=(28, "accept"))
    c3 = w.case("c3", 24, 25)
    w.case("c3b", 26, 27, verdict=(29, "accept"), revises=c3, asked_by="human")  # judged(c3) is the rework: J = 27
    w.case("c2", 22, 23, verdict=(35, "accept"))  # the last judging verdict: D = 35
    assert (p2(w).state, p2(w).clean, p2(w).waiting) == ("kept", 3, 0)
    late = w.bag.verdict(c3, 31, "reject")  # a late verdict on c3's first delivery (result 25, before E = 27), before K
    w.bag.link(late, 32, "C5")
    warned = p2(w)
    assert (warned.state, warned.related, warned.clean, warned.waiting) == ("warning", ("R2",), 2, 0)  # judged(c3) did not move


# ----------------------------------------------------------------------------------------------------------- 8.1 rows xiii-xv (R3-F1)


def delayed_verdict(w: Watching) -> tuple[Watching, Message]:
    """c1 and c2 accepted, c3 delivered without a verdict yet, c4 delivered after c3 (ask 28, done 29)."""
    w.case("c1", 20, 21, verdict=(22, "accept"))
    w.case("c2", 23, 24, verdict=(25, "accept"))
    c3 = w.case("c3", 26, 27)
    return w, c3


def test_row_xiii_a_later_case_rejected_and_linked_before_the_kth_verdict_stays_warning_after_it() -> None:
    w, c3 = delayed_verdict(setup())
    w.case("c4", 28, 29, verdict=(30, "reject"), link=(31, ["C5"]))  # recorded before c3's verdict
    before = p2(w)
    assert (before.state, before.related, before.waiting) == ("warning", ("R2",), 1)
    w.bag.verdict(c3, 40, "accept")  # E = 27, D = 40: the rejection was recorded before D
    after = p2(w)
    assert (after.state, after.related, after.waiting, after.clean) == ("warning", ("R2",), 0, 3)


def test_row_xiv_the_same_rejection_recorded_after_the_kth_verdict_is_outside_the_window() -> None:
    w, c3 = delayed_verdict(setup())
    w.bag.verdict(c3, 40, "accept")
    w.case("c4", 28, 29, verdict=(41, "reject"), link=(42, ["C5"]))  # a result after E (27), recorded after D (40)
    assert (p2(w).state, p2(w).related, p2(w).clean) == ("kept", (), 3)


def test_row_xv_a_relayed_verdict_before_the_link_and_the_human_verdict_after_it_stays_warning() -> None:
    w, c3 = delayed_verdict(setup())
    w.bag.verdict(c3, 30, "accept", source="relayed")  # root passes P2-UNRATED with its own reading: no judged(c3)
    w.case("c4", 28, 29, verdict=(31, "reject"), link=(32, ["C5"]))
    assert (p2(w).state, p2(w).waiting) == ("warning", 1)
    w.bag.verdict(c3, 40, "accept")  # the user's verdict: D is this note, so the rejection (31) is before it
    assert (p2(w).state, p2(w).related, p2(w).waiting) == ("warning", ("R2",), 0)


# ----------------------------------------------------------------------------------------------------------------------- 8.7


def test_no_playbook_gives_no_items() -> None:
    assert watch_states([], [], {}, [], []) == ()


def test_a_legacy_playbook_gives_its_virtual_items_all_kept() -> None:
    legacy = Playbook(version=1, body="1. Search.\n2. Write.", items=None)
    found = watch_states([legacy], [], {}, [], [])
    assert [(i.id, i.kind, i.state, i.text_version) for i in found] == [("P1", "step", "kept", 1), ("P2", "step", "kept", 1)]
    assert watch_states([Playbook(version=1, body="", items=None)], [], {}, [], []) == ()


def test_0_deliveries_since_the_watch_start_is_new_with_no_clean_case() -> None:
    w = setup()
    new = p2(w)
    assert (new.state, new.clean, new.waiting, new.k, new.related, new.pending, new.retire_due) == ("new", 0, 0, 3, (), (), False)
    assert new.watch_start == w.versions[1].revised and new.text_version == 2
    assert w.states()["P1"].state == "kept"  # the first version's step was never watched


def test_a_judged_case_whose_only_rejection_is_pending_is_not_clean_not_related_and_listed_pending() -> None:
    w = setup()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "reject"))  # no answer yet
    w.case("c3", 24, 25, verdict=(32, "accept"))
    held = p2(w)
    assert (held.state, held.pending, held.related, held.clean, held.waiting) == ("new", ("R2",), (), 2, 0)


def test_a_rejection_linked_none_is_unrelated_and_its_case_is_clean() -> None:
    w = setup()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "reject"), link=(33, ["none"]))
    w.case("c3", 24, 25, verdict=(32, "accept"))
    kept = p2(w)
    assert (kept.state, kept.related, kept.pending, kept.clean) == ("kept", (), (), 3)


def test_a_rejection_the_user_never_answers_keeps_the_item_new_for_good() -> None:
    w = setup()
    accepted(w)
    w.case("c4", 26, 27, verdict=(28, "reject"))  # recorded before D (32) and never answered
    assert (p2(w).state, p2(w).pending) == ("new", ("R2",))
    w.case("c5", 50, 51, verdict=(52, "accept"))  # later cases do not settle it
    assert (p2(w).state, p2(w).pending) == ("new", ("R2",))


def test_an_agent_clients_verdicts_judge_no_candidate() -> None:
    w = setup()
    for i in range(1, 4):
        w.case(f"c{i}", 20 + 2 * i, 21 + 2 * i, verdict=(40 + i, "accept"), source="agent")
    held = p2(w)
    assert (held.state, held.waiting, held.clean) == ("new", 3, 0)


def test_relayed_and_agent_verdicts_judge_no_candidate() -> None:
    w = setup()
    w.case("c1", 20, 21, verdict=(30, "accept"), source="relayed")
    w.case("c2", 22, 23, verdict=(31, "reject"), source="relayed", link=(32, ["C5"]))  # a relayed rejection is no assertion
    w.case("c3", 24, 25, verdict=(33, "accept"), source="agent")
    held = p2(w)
    assert (held.state, held.waiting, held.clean, held.related, held.pending) == ("new", 3, 0, (), ())


def test_a_contract_with_no_criteria_works_on_the_assertions_alone() -> None:
    w = Watching()  # no contract version at all
    w.versions.append(playbook(1, 10, [step("P1", "Read the request.")], op="first", admitted="first"))
    w.versions.append(playbook(2, 11, [step("P1", "Read the request."), rule("P2", "x", "y", why=("R1",))], op="add", item="P2", admitted="b"))
    w.case("c0", 1, 2, verdict=(3, "reject"), link=(4, ["none"]))  # R1: no lasting rule, about nothing
    for i in range(1, 3):
        w.case(f"c{i}", 20 + 2 * i, 21 + 2 * i, verdict=(30 + i, "accept"))
    w.case("c3", 30, 31, verdict=(40, "reject"), link=(41, ["R1"]))  # "same as R1": its subjects are R2 and R1, which P2 cites
    found = w.states()["P2"]
    assert (found.state, found.related, found.coverage) == ("warning", ("R2",), ())


def test_a_removed_criterion_is_no_coverage_but_still_a_subject_of_the_rejection_whose_answer_removed_it() -> None:
    w = setup()
    assert p2(w).coverage == ("R1", "C5")  # C5 is current, and R1 was confirmed about it
    w.case("c1", 20, 21, verdict=(30, "reject"))
    w.contracts.append(contract(2, ["a", "b", "c", "d", "f", "g"], 31, answers=w.notes["c1"].id, about="C5"))  # removes C5, adds C7
    removed = p2(w)
    assert (removed.state, removed.related, removed.coverage) == ("warning", ("R2",), ())  # no coverage: the client lowered that bar herself


def test_every_item_retired_returns_the_retired_items_only() -> None:
    w = setup()
    w.versions.append(playbook(3, 50, [step("P1", "Read the request.")], op="retire", item="P2", admitted="exempt"))
    w.versions.append(playbook(4, 51, [], op="retire", item="P1", admitted="exempt"))
    found = w.states()
    assert {i: (s.state, s.kind) for i, s in found.items()} == {"P1": ("retired", "step"), "P2": ("retired", "rule")}


def test_a_candidate_with_no_counted_verdict_holds_the_item_new() -> None:
    w = setup()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "accept"))
    w.case("c3", 24, 25, verdict=(32, "accept"), source="relayed")
    assert (p2(w).state, p2(w).waiting) == ("new", 1)


def test_a_superseded_first_delivery_holds_nothing() -> None:
    w = setup()
    accepted(w, 2)
    c3 = w.case("c3", 24, 25)  # superseded by a relayed rework before any verdict
    w.case("c3b", 26, 27, verdict=(33, "accept"), revises=c3, asked_by="relayed")
    assert (p2(w).state, p2(w).waiting) == ("kept", 0)  # counted through the delivery the user judged


def test_a_late_verdict_on_a_superseded_delivery_changes_nothing_for_judged() -> None:
    w = setup()
    accepted(w, 2)
    c3 = w.case("c3", 24, 25)
    w.case("c3b", 26, 27, verdict=(33, "accept"), revises=c3, asked_by="relayed")
    before = p2(w)
    w.bag.verdict(c3, 50, "accept")  # a late accept on the first delivery
    assert p2(w) == before


def test_a_later_case_rejected_before_the_kth_verdict_is_in_the_window_and_after_it_is_outside() -> None:
    inside, c3 = delayed_verdict(setup())
    inside.case("c4", 28, 29, verdict=(30, "reject"), link=(31, ["C5"]))
    inside.bag.verdict(c3, 40, "accept")
    outside, d3 = delayed_verdict(setup())
    outside.bag.verdict(d3, 40, "accept")
    outside.case("c4", 28, 29, verdict=(41, "reject"), link=(42, ["C5"]))
    assert (p2(inside).state, p2(outside).state) == ("warning", "kept")


def test_a_blocked_result_that_is_never_rejected_holds_nothing() -> None:
    w = setup()
    w.case("cb", 19, 20, status="blocked")
    accepted(w)
    assert (p2(w).state, p2(w).clean, p2(w).waiting) == ("kept", 3, 0)  # a blocked result is no delivery and needs no verdict


def test_two_related_rejections_set_retire_due_with_state_warning() -> None:
    w = setup()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "reject"), link=(32, ["C5"]))
    w.case("c3", 24, 25, verdict=(33, "reject"), link=(34, ["R1"]))
    due = p2(w)
    assert (due.state, due.related, due.retire_due, due.clean) == ("warning", ("R2", "R3"), True, 1)


def test_a_why_case_is_never_a_candidate() -> None:
    w = setup()
    w.case("c0b", 20, 21, verdict=(30, "accept"), revises=w.tasks["c0"], asked_by="human")  # a rework of c0, delivered after P2 went live
    w.case("c1", 22, 23, verdict=(31, "accept"))
    w.case("c2", 24, 25, verdict=(32, "accept"))
    held = p2(w)
    assert (held.state, held.clean, held.waiting) == ("new", 2, 0)  # only c1 and c2 are candidates: E stays undefined


def test_watch_states_is_a_function_of_the_files() -> None:
    w = setup()
    accepted(w, 2)
    w.case("c3", 24, 25, verdict=(35, "reject"), link=(36, ["C5"]))
    versions, cases, results = list(w.versions), w.bag.cases(), w.bag.results()
    snapshot = repr((versions, cases, results))
    first = watch_states(versions, cases, results, [], w.contracts)
    again = watch_states(versions, cases, results, [], w.contracts)
    assert first == again and repr((versions, cases, results)) == snapshot  # the same inputs give equal outputs, nothing is changed
