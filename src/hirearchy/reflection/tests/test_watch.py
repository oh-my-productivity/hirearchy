"""``watch_states`` (design 8.1, 8.2, 8.7): the state of every playbook item, derived from the versions, the cases and their results, the criteria
and the contract versions. Rows i-xxv of 8.1 and the zero and empty cases of 8.7 each have a test named after them.

World: the playbook's P2 is a rule admitted at tick 10 on R1 (case c0's rejection, answered about C5); k is 3; a request is ``w.case(name, ask,
done, verdict=(tick, kind), link=(tick, ids))``. A rejection is related to P2 when it is answered about C5 (or R1)."""

from __future__ import annotations

from hirearchy.kernel import Message
from hirearchy.reflection._watch import watch_k, watch_states
from hirearchy.services import ItemWatch, Playbook

from ._watch_kit import Watching, contract, playbook, rule, stamp, step, world


def p2(w: Watching) -> ItemWatch:
    return w.states()["P2"]


def accepted(w: Watching, n: int = 3, first: int = 20) -> None:
    """``n`` candidates delivered and accepted in turn (c1: ask 20, done 21, accept 30; c2: 22, 23, 31 ...)."""
    for i in range(1, n + 1):
        w.case(f"c{i}", first + 2 * (i - 1), first + 2 * (i - 1) + 1, verdict=(30 + i - 1, "accept"))


# ----------------------------------------------------------------------------------------------------------------- 8.1 rows i-viii


def test_row_i_a_candidate_delivered_before_the_kth_and_judged_after_it_related_is_warning_never_kept() -> None:
    w = world()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(34, "reject"))  # delivered before c3, judged after it
    w.case("c3", 24, 25, verdict=(32, "accept"))
    waiting = p2(w)
    assert (waiting.state, waiting.pending, waiting.related) == ("new", ("R2",), ())  # the answer is due: not kept, not warned yet
    w.bag.link(w.notes["c2"], 35, "C5")
    warned = p2(w)
    assert (warned.state, warned.related, warned.pending, warned.clean, warned.waiting) == ("warning", ("R2",), (), 2, 0)


def test_row_ii_the_same_candidate_unjudged_is_new_and_waiting_until_its_verdict() -> None:
    w = world()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "accept"))
    c3 = w.case("c3", 24, 25)
    held = p2(w)
    assert (held.state, held.waiting, held.clean, held.k) == ("new", 1, 2, 3)
    w.bag.verdict(c3, 40, "accept")
    assert (p2(w).state, p2(w).waiting, p2(w).clean) == ("kept", 0, 3)


def test_row_iii_a_related_rejection_after_e_and_recorded_after_d_is_outside_the_window() -> None:
    w = world()
    accepted(w)  # E is c3's delivery (25), D is c3's verdict (32)
    w.case("c4", 40, 41, verdict=(42, "reject"), link=(43, ["C5"]))  # a result after E, recorded after D
    kept = p2(w)
    assert (kept.state, kept.related, kept.clean) == ("kept", (), 3)


def test_row_iv_a_related_rejection_on_a_blocked_result_before_e_is_related() -> None:
    w = world()
    accepted(w)
    w.case("cb", 19, 20, status="blocked", verdict=(28, "reject"), link=(29, ["C5"]))  # a blocked result is no delivery, but a file from it can be rejected
    warned = p2(w)
    assert (warned.state, warned.related, warned.clean) == ("warning", ("R2",), 3)  # cb is no candidate: c1-c3 are clean


def test_row_v_a_first_delivery_superseded_by_a_human_rework_the_user_accepts_is_clean() -> None:
    w = world()
    c1 = w.case("c1", 20, 21)  # delivered, superseded before any verdict
    w.case("c1b", 22, 23, verdict=(33, "accept"), revises=c1, asked_by="human")
    w.case("c2", 24, 25, verdict=(30, "accept"))
    w.case("c3", 26, 27, verdict=(31, "accept"))
    kept = p2(w)
    assert (kept.state, kept.clean, kept.waiting) == ("kept", 3, 0)  # judged(c1) is the rework


def test_row_vi_a_relayed_rework_the_user_rejects_about_the_items_refs_is_related() -> None:
    w = world()
    c1 = w.case("c1", 20, 21)
    w.case("c1b", 22, 23, verdict=(33, "reject"), link=(34, ["C5"]), revises=c1, asked_by="relayed")
    w.case("c2", 24, 25, verdict=(30, "accept"))
    w.case("c3", 26, 27, verdict=(31, "accept"))
    warned = p2(w)
    assert (warned.state, warned.related, warned.clean) == ("warning", ("R2",), 2)


def test_row_vii_the_kth_candidates_rework_rejected_about_the_item_is_related_inside_the_window() -> None:
    w = world()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "accept"))
    c3 = w.case("c3", 24, 25)  # its first delivery is superseded by a rework
    w.case("c3b", 26, 29, verdict=(40, "reject"), link=(41, ["C5"]), revises=c3, asked_by="relayed")  # E is 29, D is the rejection's note
    warned = p2(w)
    assert (warned.state, warned.related, warned.waiting) == ("warning", ("R2",), 0)


def test_row_viii_a_late_verdict_on_the_superseded_first_delivery_leaves_judged_e_and_d_and_is_related_before_k() -> None:
    w = world()
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
    w, c3 = delayed_verdict(world())
    w.case("c4", 28, 29, verdict=(30, "reject"), link=(31, ["C5"]))  # recorded before c3's verdict
    before = p2(w)
    assert (before.state, before.related, before.waiting) == ("warning", ("R2",), 1)
    w.bag.verdict(c3, 40, "accept")  # E = 27, D = 40: the rejection was recorded before D
    after = p2(w)
    assert (after.state, after.related, after.waiting, after.clean) == ("warning", ("R2",), 0, 3)


def test_row_xiv_the_same_rejection_recorded_after_the_kth_verdict_is_outside_the_window() -> None:
    w, c3 = delayed_verdict(world())
    w.bag.verdict(c3, 40, "accept")
    w.case("c4", 28, 29, verdict=(41, "reject"), link=(42, ["C5"]))  # a result after E (27), recorded after D (40)
    assert (p2(w).state, p2(w).related, p2(w).clean) == ("kept", (), 3)


def test_row_xv_a_relayed_verdict_before_the_link_and_the_human_verdict_after_it_stays_warning() -> None:
    w, c3 = delayed_verdict(world())
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
    w = world()
    new = p2(w)
    assert (new.state, new.clean, new.waiting, new.k, new.related, new.pending, new.retire_due) == ("new", 0, 0, 3, (), (), False)
    assert new.watch_start == w.versions[1].revised and new.text_version == 2
    assert w.states()["P1"].state == "kept"  # the first version's step was never watched


def test_a_judged_case_whose_only_rejection_is_pending_is_not_clean_not_related_and_listed_pending() -> None:
    w = world()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "reject"))  # no answer yet
    w.case("c3", 24, 25, verdict=(32, "accept"))
    held = p2(w)
    assert (held.state, held.pending, held.related, held.clean, held.waiting) == ("new", ("R2",), (), 2, 0)


def test_a_rejection_linked_none_is_unrelated_and_its_case_is_clean() -> None:
    w = world()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "reject"), link=(33, ["none"]))
    w.case("c3", 24, 25, verdict=(32, "accept"))
    kept = p2(w)
    assert (kept.state, kept.related, kept.pending, kept.clean) == ("kept", (), (), 3)


def test_a_rejection_the_user_never_answers_keeps_the_item_new_for_good() -> None:
    w = world()
    accepted(w)
    w.case("c4", 26, 27, verdict=(28, "reject"))  # recorded before D (32) and never answered
    assert (p2(w).state, p2(w).pending) == ("new", ("R2",))
    w.case("c5", 50, 51, verdict=(52, "accept"))  # later cases do not settle it
    assert (p2(w).state, p2(w).pending) == ("new", ("R2",))


def test_an_agent_clients_verdicts_judge_no_candidate() -> None:
    w = world()
    for i in range(1, 4):
        w.case(f"c{i}", 20 + 2 * i, 21 + 2 * i, verdict=(40 + i, "accept"), source="agent")
    held = p2(w)
    assert (held.state, held.waiting, held.clean) == ("new", 3, 0)


def test_relayed_and_agent_verdicts_judge_no_candidate() -> None:
    w = world()
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
    w = world()
    assert p2(w).coverage == ("R1", "C5")  # C5 is current, and R1 was confirmed about it
    w.case("c1", 20, 21, verdict=(30, "reject"))
    w.contracts.append(contract(2, ["a", "b", "c", "d", "f", "g"], 31, answers=w.notes["c1"].id, about="C5"))  # removes C5, adds C7
    removed = p2(w)
    assert (removed.state, removed.related, removed.coverage) == ("warning", ("R2",), ())  # no coverage: the client lowered that bar herself


def test_every_item_retired_returns_the_retired_items_only() -> None:
    w = world()
    w.versions.append(playbook(3, 50, [step("P1", "Read the request.")], op="retire", item="P2", admitted="exempt"))
    w.versions.append(playbook(4, 51, [], op="retire", item="P1", admitted="exempt"))
    found = w.states()
    assert {i: (s.state, s.kind) for i, s in found.items()} == {"P1": ("retired", "step"), "P2": ("retired", "rule")}


def retired_at_40(w: Watching) -> None:
    """P2 is retired by its owner (v3, tick 40); the cases below are judged, left waiting and left pending before it."""
    w.versions.append(playbook(3, 40, [w.items(1)[0]], op="retire", item="P2", admitted="exempt"))


def test_a_retired_items_clean_waiting_and_pending_stop_at_the_retiring_version() -> None:
    """F-P1-6 (design 10.6): after the retire, a verdict, a link or a delivery moves nothing in ``clean``, ``waiting`` and ``pending``."""
    w = world()
    w.case("c1", 20, 21, verdict=(30, "accept"))  # clean
    w.case("c2", 22, 23)  # delivered, no verdict: waiting
    w.case("c3", 24, 25, verdict=(26, "reject"))  # judged, not yet answered: pending, and not clean
    retired_at_40(w)
    at_retire = p2(w)
    assert (at_retire.state, at_retire.clean, at_retire.waiting, at_retire.pending) == ("retired", 1, 1, ("R2",))
    assert at_retire.retired_in == 3  # the version that retired it
    w.bag.verdict(w.tasks["c2"], 50, "accept")  # the waiting case is judged after the retire ...
    w.bag.link(w.notes["c3"], 51, "none")  # ... the pending rejection is answered ...
    w.case("c4", 52, 53, verdict=(54, "accept"))  # ... and a later case is delivered and accepted
    later = p2(w)
    assert (later.state, later.clean, later.waiting, later.pending) == ("retired", 1, 1, ("R2",))


def test_a_later_verdict_does_not_move_a_retired_items_counts() -> None:
    w = world()
    w.case("c1", 20, 21)  # delivered, no verdict
    retired_at_40(w)
    assert (p2(w).clean, p2(w).waiting) == (0, 1)
    w.bag.verdict(w.tasks["c1"], 60, "accept")
    assert (p2(w).state, p2(w).clean, p2(w).waiting) == ("retired", 0, 1)


def test_related_of_a_retired_item_is_unchanged() -> None:
    """The watch's ``related`` is still read over all the files, as in Phase 1: a rejection linked after the retire is related to the retired text."""
    w = world()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "reject"))
    retired_at_40(w)
    assert p2(w).related == ()
    w.bag.link(w.notes["c2"], 50, "C5")
    assert (p2(w).state, p2(w).related) == ("retired", ("R2",))


def test_a_candidate_with_no_counted_verdict_holds_the_item_new() -> None:
    w = world()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "accept"))
    w.case("c3", 24, 25, verdict=(32, "accept"), source="relayed")
    assert (p2(w).state, p2(w).waiting) == ("new", 1)


def test_a_superseded_first_delivery_holds_nothing() -> None:
    w = world()
    accepted(w, 2)
    c3 = w.case("c3", 24, 25)  # superseded by a relayed rework before any verdict
    w.case("c3b", 26, 27, verdict=(33, "accept"), revises=c3, asked_by="relayed")
    assert (p2(w).state, p2(w).waiting) == ("kept", 0)  # counted through the delivery the user judged


def test_a_late_verdict_on_a_superseded_delivery_changes_nothing_for_judged() -> None:
    w = world()
    accepted(w, 2)
    c3 = w.case("c3", 24, 25)
    w.case("c3b", 26, 27, verdict=(33, "accept"), revises=c3, asked_by="relayed")
    before = p2(w)
    w.bag.verdict(c3, 50, "accept")  # a late accept on the first delivery
    assert p2(w) == before


def test_a_later_case_rejected_before_the_kth_verdict_is_in_the_window_and_after_it_is_outside() -> None:
    inside, c3 = delayed_verdict(world())
    inside.case("c4", 28, 29, verdict=(30, "reject"), link=(31, ["C5"]))
    inside.bag.verdict(c3, 40, "accept")
    outside, d3 = delayed_verdict(world())
    outside.bag.verdict(d3, 40, "accept")
    outside.case("c4", 28, 29, verdict=(41, "reject"), link=(42, ["C5"]))
    assert (p2(inside).state, p2(outside).state) == ("warning", "kept")


def test_a_blocked_result_that_is_never_rejected_holds_nothing() -> None:
    w = world()
    w.case("cb", 19, 20, status="blocked")
    accepted(w)
    assert (p2(w).state, p2(w).clean, p2(w).waiting) == ("kept", 3, 0)  # a blocked result is no delivery and needs no verdict


def test_two_related_rejections_set_retire_due_with_state_warning() -> None:
    w = world()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "reject"), link=(32, ["C5"]))
    w.case("c3", 24, 25, verdict=(33, "reject"), link=(34, ["R1"]))
    due = p2(w)
    assert (due.state, due.related, due.retire_due, due.clean) == ("warning", ("R2", "R3"), True, 1)


def test_a_why_case_is_never_a_candidate() -> None:
    w = world()
    w.case("c0b", 20, 21, verdict=(30, "accept"), revises=w.tasks["c0"], asked_by="human")  # a rework of c0, delivered after P2 went live
    w.case("c1", 22, 23, verdict=(31, "accept"))
    w.case("c2", 24, 25, verdict=(32, "accept"))
    held = p2(w)
    assert (held.state, held.clean, held.waiting) == ("new", 2, 0)  # only c1 and c2 are candidates: E stays undefined


def test_watch_states_is_a_function_of_the_files() -> None:
    w = world()
    accepted(w, 2)
    w.case("c3", 24, 25, verdict=(35, "reject"), link=(36, ["C5"]))
    versions, cases, results = list(w.versions), w.bag.cases(), w.bag.results()
    snapshot = repr((versions, cases, results))
    first = watch_states(versions, cases, results, [], w.contracts)
    again = watch_states(versions, cases, results, [], w.contracts)
    assert first == again and repr((versions, cases, results)) == snapshot  # the same inputs give equal outputs, nothing is changed


# ------------------------------------------------------------------------------------------------ 8.1 rows xvi-xx: K and the warned window


def test_row_xvi_a_rejection_recorded_after_k_leaves_kept() -> None:
    w = world()
    accepted(w)  # D is c3's verdict (32): the files up to it derive kept, so K = 32
    assert p2(w).state == "kept"
    late = w.bag.verdict(w.tasks["c2"], 40, "reject")  # a second verdict on c2's judged delivery (result 23, before E), recorded after K
    w.bag.link(late, 41, "C5")
    kept = p2(w)
    assert (kept.state, kept.related, kept.clean) == ("kept", (), 3)  # after the watch: nothing recorded later joins the window


def test_row_xvii_a_pending_rejection_at_d_then_a_related_one_is_warning() -> None:
    w = world()
    accepted(w)  # D = 32
    w.case("c4", 26, 27, verdict=(28, "reject"))  # R2: in the window (recorded before D) and pending
    assert (p2(w).state, p2(w).pending) == ("new", ("R2",))  # K is not reached while it is pending
    later = w.bag.verdict(w.tasks["c1"], 40, "reject")  # R3: a second verdict on c1's judged delivery (result 21, before E)
    w.bag.link(later, 41, "C5")
    w.bag.link(w.notes["c4"], 50, "none")  # R2 answered, unrelated: the files up to here still hold R3 related
    warned = p2(w)
    assert (warned.state, warned.related, warned.pending) == ("warning", ("R3",), ())


def test_row_xix_a_corrected_link_after_k_is_warning_and_a_second_the_retire() -> None:
    w = world()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "reject"), link=(33, ["none"]))  # R2: no lasting rule
    w.case("c3", 24, 25, verdict=(32, "reject"), link=(34, ["none"]))  # R3: the same; K is 34
    assert (p2(w).state, p2(w).related) == ("kept", ())
    w.bag.link(w.notes["c2"], 40, "C5")  # the user corrects the link of R2: it is about C5
    one = p2(w)
    assert (one.state, one.related, one.retire_due) == ("warning", ("R2",), False)
    w.bag.link(w.notes["c3"], 41, "C5")  # and of R3
    two = p2(w)
    assert (two.state, two.related, two.retire_due) == ("warning", ("R2", "R3"), True)


def row_xx(order: tuple[str, ...]) -> ItemWatch:
    """B1, k = 3: R2 (c2's rejection) warns P2 inside the window; R3, on a delivery after E (c4: done 27), is the second related rejection. The
    four records that can come in any order are c3's verdict, R2's answer, R3 and R3's answer."""
    w = world()
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "reject"))
    c3 = w.case("c3", 24, 25)
    c4 = w.case("c4", 26, 27)
    for tick, record in enumerate(order, start=100):
        if record == "verdict":
            w.bag.verdict(c3, tick, "accept")
        elif record == "answer":
            w.bag.link(w.notes["c2"], tick, "C5")
        elif record == "rejection":
            w.notes["c4"] = w.bag.verdict(c4, tick, "reject")
        else:
            w.bag.link(w.notes["c4"], tick, "C5")
    return p2(w)


def test_row_xx_a_second_related_rejection_of_a_later_delivery_after_d_is_due_in_every_order() -> None:
    """B1: whatever the order root records the k-th verdict, the first rejection's answer and the later rejection in, the second one retires it."""
    from itertools import permutations

    orders = [o for o in permutations(("verdict", "answer", "rejection", "link")) if o.index("rejection") < o.index("link")]
    assert len(orders) == 12
    for order in orders:
        due = row_xx(order)
        assert (due.state, due.related, due.retire_due) == ("warning", ("R2", "R3"), True), order


# ----------------------------------------------------------------------------------------------- 8.1 W1-W3, carried watches (B2), restored


def warned(w: Watching) -> None:
    """c1 accepted; c2 rejected and linked to C5 (R2): P2 is in ``warning``."""
    w.case("c1", 20, 21, verdict=(30, "accept"))
    w.case("c2", 22, 23, verdict=(31, "reject"), link=(32, ["C5"]))


def second_rejection(w: Watching, name: str = "c3", first: int = 50) -> None:
    """A later request, delivered and rejected about C5: the second related rejection."""
    w.case(name, first, first + 1, verdict=(first + 2, "reject"), link=(first + 3, ["C5"]))


def test_row_ix_a_moved_then_reformatted_warned_item_is_retired_in_its_current_text() -> None:
    """W1: a move and a formatting edit keep the watched change; the second related rejection is read against the text that is live now."""
    w = world()
    warned(w)
    p1, rule2 = w.versions[1].items or ()
    w.versions.append(playbook(3, 40, [rule2, p1], op="move", item="P2", admitted="exempt"))
    reformatted = rule("P2", "A date is relative", "Convert it from the date of the request.", why=("R1", "C5"))
    w.versions.append(playbook(4, 41, [reformatted, p1], op="edit", item="P2", admitted="exempt"))
    second_rejection(w)
    due = p2(w)
    assert (due.state, due.related, due.retire_due, due.text_version, due.watch_start) == ("warning", ("R2", "R3"), True, 2, w.versions[1].revised)


def test_row_x_an_exempt_restore_restarts_the_watch_with_the_warning_kept() -> None:
    """W2: a client-written text restored while the item is in its watch is a change of the text like any other: the clean count restarts, the
    related rejections found so far stay, and the next related rejection retires the restored text."""
    w = world(p1="Read the request; check every date (C5).")
    v1_text = step("P1", "Read the request; check every date (C5).")
    edited = step("P1", "Read the request and check every date against the notes.", ("R1", "C5"))
    w.versions.append(playbook(3, 12, [edited, w.items(1)[1]], op="edit", item="P1", admitted="c"))  # P1 on trial from tick 12
    warned(w)
    assert w.states()["P1"].state == "warning"
    w.versions.append(playbook(4, 40, [v1_text, w.items(1)[1]], op="restore", item="P1", admitted="restore", restores=1))
    restored = w.states()["P1"]
    assert (restored.state, restored.related, restored.clean, restored.text_version) == ("warning", ("R2",), 0, 4)
    assert restored.watch_start == w.versions[2].revised  # the watch is the one that began at tick 12
    second_rejection(w)
    due = w.states()["P1"]
    assert (due.state, due.related, due.retire_due) == ("warning", ("R2", "R3"), True)


def retired_in_warning(w: Watching) -> None:
    """P2 warned (R2), then its owner retires it (v3, tick 40)."""
    warned(w)
    w.versions.append(playbook(3, 40, [w.items(1)[0]], op="retire", item="P2", admitted="exempt"))


def test_row_xi_a_restore_or_an_add_after_an_owners_retire_in_warning_is_carried() -> None:
    w = world()
    retired_in_warning(w)
    p1, old = w.versions[1].items or ()
    w.versions.append(playbook(4, 41, [p1, old], op="restore", item="P2", admitted="c", restores=2))
    back = p2(w)
    assert (back.state, back.carried, back.related, back.clean, back.watch_start) == ("warning", "P2", ("R2",), 0, w.versions[1].revised)
    v = world()
    retired_in_warning(v)
    added = rule("P5", "always", "convert it from the date of the request.", why=("R1", "C5"))  # P2's words, another id and condition
    v.versions.append(playbook(4, 41, [v.items(1)[0], added], op="add", item="P5", admitted="c"))
    found = v.states()
    assert (found["P2"].state, found["P5"].state, found["P5"].carried, found["P5"].related) == ("retired", "warning", "P2", ("R2",))


def test_row_xii_a_repaired_item_whose_line_was_untouched_carries_its_watch() -> None:
    w = world()
    warned(w)
    w.versions.append(playbook(3, 40, [], op="", parse_error="line 3: a hand edit"))
    repaired = [
        step("P3", "[P1] Read the request."),
        step("P4", "[P2] WHEN a date is relative THEN convert it from the date of the request WHY R1, C5"),
    ]
    w.versions.append(playbook(4, 45, repaired, op="migrate", admitted="migrate"))
    found = w.states()
    assert (found["P1"].state, found["P2"].state) == ("retired", "retired")
    assert (found["P3"].state, found["P3"].carried) == ("kept", "")
    assert (found["P4"].state, found["P4"].carried, found["P4"].related, found["P4"].watch_start) == ("warning", "P2", ("R2",), w.versions[1].revised)
    second_rejection(w)
    assert (w.states()["P4"].state, w.states()["P4"].retire_due) == ("warning", True)  # one more related rejection retires it


def test_row_xxi_a_gated_edit_of_another_item_into_a_warned_retired_text_is_carried_with_its_own_rejections() -> None:
    """B2: P3 is on trial for its own related rejection (R3, about C6); the owner retires P2 in warning, then edits P3 into P2's text."""
    w = world()
    p1, rule2 = w.versions[1].items or ()
    rule3 = rule("P3", "a total is stated", "check it twice", why=("C6",))
    w.versions.append(playbook(3, 12, [p1, rule2, rule3], op="add", item="P3", admitted="c"))
    w.case("c1", 20, 21, verdict=(30, "reject"), link=(31, ["C5"]))  # R2: P2's first related rejection
    w.case("c2", 22, 23, verdict=(32, "reject"), link=(33, ["C6"]))  # R3: P3's own
    w.versions.append(playbook(4, 40, [p1, rule3], op="retire", item="P2", admitted="exempt"))
    into = rule("P3", "a date is relative", rule2.text, why=("R1", "C5"))
    w.versions.append(playbook(5, 41, [p1, into], op="edit", item="P3", admitted="c"))
    found = w.states()
    assert (found["P2"].state, found["P2"].related) == ("retired", ("R2",))
    assert (found["P3"].state, found["P3"].carried, found["P3"].related) == ("warning", "P2", ("R2", "R3"))  # the union of both


def test_a_rules_text_key_is_its_thens() -> None:
    """B2: a rule re-added as a step with its ``then``'s words is caught; other words are not."""
    w = world()
    retired_in_warning(w)
    p1, rule2 = w.versions[1].items or ()
    w.versions.append(playbook(4, 41, [p1, step("P5", "Convert it from the date of the request!", ("R1", "C5"))], op="add", item="P5", admitted="c"))
    w.versions.append(playbook(5, 42, [p1, step("P5", "Convert it from the date of the request!", ("R1", "C5")), step("P6", "Another thing.", ("R1", "C5"))], op="add", item="P6", admitted="c"))
    found = w.states()
    assert (found["P5"].carried, found["P5"].state, found["P5"].related) == ("P2", "warning", ("R2",))
    assert (found["P6"].carried, found["P6"].state, found["P6"].related) == ("", "new", ())
    assert rule2.text.lower().startswith("convert")


def test_a_restarted_watch_reads_the_union_of_its_windows() -> None:
    w = world()
    warned(w)
    p1, rule2 = w.versions[1].items or ()
    edited = rule("P2", "a date is relative", "convert it from the date of the request, and say so", why=("R1", "C5"))
    w.versions.append(playbook(3, 40, [p1, edited], op="edit", item="P2", admitted="c"))
    restarted = p2(w)  # D4: a warning survives every edit; the clean count restarts
    assert (restarted.state, restarted.related, restarted.clean, restarted.text_version, restarted.watch_start) == (
        "warning", ("R2",), 0, 3, w.versions[1].revised,
    )
    w.case("c5", 50, 51, verdict=(55, "accept"))
    w.case("c6", 52, 53, verdict=(56, "reject"), link=(57, ["C5"]))  # a related rejection in the new window
    later = p2(w)
    assert (later.state, later.related, later.retire_due, later.clean, later.waiting) == ("warning", ("R2", "R3"), True, 1, 0)


def test_a_watch_retire_without_a_previous_text_reads_retired() -> None:
    w = world()
    w.case("c1", 20, 21, verdict=(30, "reject"), link=(31, ["C5"]))
    w.case("c2", 22, 23, verdict=(32, "reject"), link=(33, ["C5"]))
    w.versions.append(playbook(3, 40, [w.items(1)[0]], op="watch", item="P2", admitted="watch", related=("R2", "R3")))
    gone = p2(w)
    assert (gone.state, gone.related, gone.retire_due, gone.restores) == ("retired", ("R2", "R3"), False, 0)
    assert gone.retires == ((3, ("R2", "R3")),)  # the retire v3 and the rejections still related to the watch it ended


def test_a_watch_retire_keeps_its_rejections_whatever_the_id_does_next() -> None:
    """F1 (design 8.6): ``retires`` is derived from the watch each retire ended, so a later watch of the same id (a gated change) or an exempt restore
    that leaves it unwatched does not change it; a user's corrected link undoes the relation (L9)."""
    w = world()
    p1, rule2 = w.versions[1].items or ()
    text_b = rule("P2", "a date is relative", "convert it, and write the date down", why=("R1", "C5"))
    w.versions.append(playbook(3, 12, [p1, text_b], op="edit", item="P2", admitted="c"))
    w.case("c1", 20, 21, verdict=(30, "reject"), link=(31, ["C5"]))
    w.case("c2", 22, 23, verdict=(32, "reject"), link=(33, ["C5"]))
    w.versions.append(playbook(4, 40, [p1, rule2], op="watch", item="P2", admitted="watch", restores=2, related=("R2", "R3")))
    assert p2(w).retires == ((4, ("R2", "R3")),)
    w.versions.append(playbook(5, 41, [p1, rule("P2", "a date is relative", "convert it twice", why=("R1", "C5"))], op="edit", item="P2", admitted="c"))
    fresh = p2(w)
    assert (fresh.state, fresh.related, fresh.retires) == ("new", (), ((4, ("R2", "R3")),))  # the new watch has no related rejection; the retire keeps its
    w.versions.append(playbook(6, 42, [p1], op="retire", item="P2", admitted="exempt"))
    w.versions.append(playbook(7, 43, [p1, rule("P2", "a date is relative", "convert it twice", why=("R1", "C5"))], op="restore", item="P2", admitted="restore", restores=5))
    assert p2(w).retires == ((4, ("R2", "R3")),)  # retired and restored outside a watch: the id's watch is gone, the retire's rejections are not
    w.bag.link(w.notes["c1"], 60, "none")  # R2's link is corrected: it is related no more
    assert p2(w).retires == ((4, ("R3",)),)


def test_an_owner_retire_while_the_watch_retire_was_due_keeps_its_rejections_but_one_made_when_it_was_not_does_not() -> None:
    """F1: an owner's retire counts only when 2 related rejections stood at the retire (the runtime's retire was due); one made with a single related
    rejection, or of a text whose watch already ended, has none, however many rejections come later."""
    due = world()
    due.case("c1", 20, 21, verdict=(30, "reject"), link=(31, ["C5"]))
    due.case("c2", 22, 23, verdict=(32, "reject"), link=(33, ["C5"]))
    due.versions.append(playbook(3, 40, [due.items(1)[0]], op="retire", item="P2", admitted="exempt"))
    assert p2(due).retires == ((3, ("R2", "R3")),)
    quiet = world()
    quiet.case("c1", 20, 21, verdict=(30, "reject"), link=(31, ["C5"]))
    quiet.versions.append(playbook(3, 40, [quiet.items(1)[0]], op="retire", item="P2", admitted="exempt"))
    quiet.case("c2", 42, 43, verdict=(44, "reject"), link=(45, ["C5"]))  # a second related rejection, recorded after the retire
    assert p2(quiet).retires == ()


def test_restored_lasts_until_a_gated_change() -> None:
    w = world()
    p1, rule2 = w.versions[1].items or ()
    text_b = rule("P2", "a date is relative", "convert it, and write the date down", why=("R1", "C5"))
    w.versions.append(playbook(3, 12, [p1, text_b], op="edit", item="P2", admitted="c"))
    w.case("c1", 20, 21, verdict=(30, "reject"), link=(31, ["C5"]))
    w.case("c2", 22, 23, verdict=(32, "reject"), link=(33, ["C5"]))
    w.versions.append(playbook(4, 40, [p1, rule2], op="watch", item="P2", admitted="watch", restores=2, related=("R2", "R3")))
    back = p2(w)
    assert (back.state, back.restores, back.related, back.retire_due) == ("restored", 2, ("R2", "R3"), False)
    w.versions.append(playbook(5, 41, [p1, rule("P2", "A date is relative", rule2.text + ".", why=("R1", "C5"))], op="edit", item="P2", admitted="exempt"))
    assert p2(w).state == "restored"  # a formatting fix is no gated change
    w.versions.append(playbook(6, 42, [p1, rule("P2", "a date is relative", "convert it twice", why=("R1", "C5"))], op="edit", item="P2", admitted="c"))
    fresh = p2(w)
    assert (fresh.state, fresh.restores, fresh.related, fresh.watch_start) == ("new", 0, (), w.versions[5].revised)


def test_a_gated_change_of_a_kept_item_starts_a_new_watch_and_an_exempt_restore_leaves_it_kept() -> None:
    w = world()
    accepted(w)
    assert p2(w).state == "kept"
    p1, rule2 = w.versions[1].items or ()
    w.versions.append(playbook(3, 40, [p1, rule("P2", "a date is relative", "convert it twice", why=("R1", "C5"))], op="restore", item="P2", admitted="restore", restores=2))
    assert (p2(w).state, p2(w).watch_start) == ("kept", w.versions[1].revised)  # outside a watch, an exempt restore leaves it kept
    w.versions.append(playbook(4, 41, [p1, rule("P2", "a date is relative", "convert it thrice", why=("R1", "C5"))], op="edit", item="P2", admitted="c"))
    fresh = p2(w)
    assert (fresh.state, fresh.clean, fresh.related, fresh.watch_start, fresh.text_version) == ("new", 0, (), w.versions[3].revised, 4)
    assert rule2.id == "P2"


# ----------------------------------------------------------------------------------------------------------------------- 8.4: k and r


def history(judged: int, failed: int, *, linked: bool = True) -> Watching:
    """``judged`` cases judged before P2 goes on trial at tick 1000, ``failed`` of them rejected (R1 ...) and answered about C5 (P2 cites C5).
    Case i: ask 10 i, done 10 i + 1, verdict 10 i + 2, link 10 i + 3."""
    w = Watching()
    w.contracts.append(contract(1, ["a", "b", "c", "d", "e", "f"], 0))
    first = [step("P1", "Read the request.")]
    w.versions.append(playbook(1, 0, first, op="first", admitted="first"))
    for i in range(1, judged + 1):
        bad = i <= failed
        w.case(f"h{i}", 10 * i, 10 * i + 1, verdict=(10 * i + 2, "reject" if bad else "accept"), link=(10 * i + 3, ["C5"]) if bad and linked else None)
    w.versions.append(playbook(2, 1000, [*first, rule("P2", "a date is relative", "convert it", why=("C5",))], op="add", item="P2", admitted="c"))
    return w


def test_k_is_3_while_r_is_unknown() -> None:
    w = world()
    found = p2(w)
    assert (found.k, found.r) == (3, (1, 1))  # one judged case before the watch start (c0, rejected about C5): below 10, r is unknown
    assert w.states()["P1"].k == 0  # never watched: no k


def test_k_is_4_7_11_22_for_r_of_0_5_0_3_0_2_0_1() -> None:
    for failed, expected in ((5, 4), (3, 7), (2, 11), (1, 22)):
        found = history(10, failed).states()["P2"]
        assert (found.k, found.r) == (expected, (failed, 10)), failed
    assert watch_k(10, 10) == 3  # r = 1 gives 3
    assert watch_k(9, 10) == 3  # ln 0.1 / ln 0.1 is 1: the floor of 3 holds
    assert [watch_k(f, 1000) for f in (1, 10, 100)] == [2302, 230, 22]  # never capped


def test_r_is_unknown_below_10_judged_cases_or_without_a_failure() -> None:
    assert (lambda f: (f.k, f.r))(history(9, 3).states()["P2"]) == (3, (3, 9))  # a failure seen 3 times in 9 cases: noise
    assert (lambda f: (f.k, f.r))(history(10, 0).states()["P2"]) == (3, (0, 10))  # 10 cases, none failed
    assert (lambda f: (f.k, f.r))(history(12, 12).states()["P2"]) == (3, (12, 12))  # r = 1


def test_a_link_note_recorded_after_the_watch_start_leaves_r_and_k() -> None:
    w = history(10, 3, linked=False)  # three rejections nobody has answered at tick 1000
    before = w.states()["P2"]
    assert (before.k, before.r) == (3, (0, 10))
    for i in (1, 2, 3):
        w.bag.link(w.notes[f"h{i}"], 1100 + i, "C5")  # the user answers them after P2 went on trial
    after = w.states()["P2"]
    assert (after.k, after.r) == (3, (0, 10))  # the data as it stood at the watch start


def test_an_answering_version_defined_after_the_watch_start_leaves_r_and_k() -> None:
    """Row xxii (B3): the contract's ``created`` is v1's; only ``defined`` says when the answering version was written."""
    w = history(10, 3, linked=False)
    for i in (1, 2, 3):
        w.contracts.append(contract(1 + i, ["a", "b", "c", "d", "e", "f", f"x{i}"], 1100 + i, answers=w.notes[f"h{i}"].id, about="C5", created=stamp(0)))
    found = w.states()["P2"]
    assert (found.k, found.r) == (3, (0, 10))
    assert found.related == ()  # and the answers do not relate rejections that were outside the window
    edited = rule("P2", "a date is relative", "convert it twice", why=("C5",))
    w.versions.append(playbook(3, 1200, [step("P1", "Read the request."), edited], op="edit", item="P2", admitted="c"))
    assert (w.states()["P2"].k, w.states()["P2"].r) == (3, (0, 10))  # an edit within the watch does not change r or k
