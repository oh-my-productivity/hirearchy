"""The recording-order property of the watch (design 20, 8.1's monotonicity property; standard library only).

For each seed of a fixed list, a generated watch: k = 3, the item P2 live from before the first delivery, five requests delivered up front (three
candidates, a later delivery after E and a blocked result before it), and at most 7 records to append: the human verdicts of the candidates,
root's relayed verdict, a rejection of another case, a second verdict on a judged delivery, and the answers to the rejections (a link naming the
item's criterion, ``none``, "same as" an earlier rejection, or an answering contract version). Every order that keeps each answer after its
rejection is stamped in that order and ``watch_states`` is read after each record.

Asserted: (1) the state moves only along ``new -> kept``, ``new -> warning -> retire due`` and ``warning`` held; (2) the final state equals the one
derived from scratch from the same files (read in another order); (3) with one corrected link inserted, the only move outside (1) is at that
record; (4) B1: a second related rejection on a delivery made after E and recorded after D, of an item a first related rejection warned, ends
``retire due`` in every order."""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations

from hirearchy.kernel import Message
from hirearchy.reflection._watch import watch_states
from hirearchy.services import ItemWatch, number_criteria

from ._watch_kit import Watching, contract, rule, world
from ._watch_stream import FULL_NAMES, INITIALS, NOTE, Stream

SEEDS = (33, 53, 20, 21, 58, 81, 15, 25)  # the generated watches: 60 to 840 admissible orders each, 2 to 7 records
CORRECTED_SEEDS = (5, 11, 37, 68, 90)  # watches with one corrected link inserted: the user's second link on a rejection
B1_SEEDS = (1, 2)  # watches built around B1's second related rejection (the first with root's relayed verdict too: 7 records)
MAX_RECORDS = 7
ACCEPTANCE = ["a", "b", "c", "d", "f", "g"]  # the version an answer writes: it removes C5 ("e") and adds C7
PATHS = {"new": {"new", "kept", "warning", "due"}, "warning": {"warning", "due"}, "due": {"due"}, "kept": {"kept"}}


@dataclass(frozen=True)
class Rec:
    """One record to append: a verdict note on a case, a relayed verdict, a link note on a rejection, or an answering contract version."""

    key: str
    kind: str  # "verdict" | "relayed" | "link" | "version"
    case: str = ""  # the request a verdict is on, or the key of the rejection a link or version answers
    verdict: str = "accept"
    ids: tuple[str, ...] = ()  # a link's ids; "@x" is the R id of the rejection with key x
    needs: tuple[str, ...] = ()  # keys that must come before it


def label(found: ItemWatch) -> str:
    return "due" if found.retire_due else found.state


def scenario(seed: int, *, b1: bool = False, corrected: bool = False) -> list[Rec]:
    """The records of one generated watch (at most ``MAX_RECORDS``)."""
    rng = random.Random(seed)
    if b1:  # R2 warns P2 inside the window; R3, on c4 (delivered after E), is the second related rejection
        recs = [Rec("v:c1", "verdict", "c1"), Rec("v:c2", "verdict", "c2", "reject"), Rec("v:c3", "verdict", "c3"),
                Rec("l:v:c2", "link", "v:c2", ids=("C5",), needs=("v:c2",)), Rec("x:c4", "verdict", "c4", "reject"),
                Rec("l:x:c4", "link", "x:c4", ids=("C5",), needs=("x:c4",))]
        if rng.random() < 0.5:
            recs.append(Rec("rl:c3", "relayed", "c3"))
        return recs
    recs = [Rec(f"v:{c}", "verdict", c, "reject" if rng.random() < 0.35 else "accept") for c in ("c1", "c2", "c3")]
    if rng.random() < 0.4:
        recs.append(Rec("rl:c3", "relayed", "c3"))
    for extra in rng.sample(["x:c4", "x:cb", "s:c2"], k=rng.choice([1, 2])):
        if extra == "s:c2":
            recs.append(Rec(extra, "verdict", "c2", "reject", needs=("v:c2",)))  # a second verdict on c2's judged delivery
        else:
            recs.append(Rec(extra, "verdict", extra[2:], "reject"))
    rejections = [r for r in recs if r.kind == "verdict" and r.verdict == "reject"]
    version_given = False
    for r in rejections:
        if rng.random() < 0.85:
            others = [o for o in rejections if o is not r]
            ids = rng.choice([("C5",), ("none",), ("R1",)] + ([(f"@{o.key}",) for o in others] if others else []))
            if not version_given and rng.random() < 0.2:
                version_given = True
                recs.append(Rec(f"a:{r.key}", "version", r.key, needs=(r.key,)))
            else:
                recs.append(Rec(f"l:{r.key}", "link", r.key, ids=ids, needs=(r.key, *(o[1:] for o in ids if o.startswith("@")))))
    recs = recs[: MAX_RECORDS - 1 if corrected else MAX_RECORDS]
    linked = [r for r in recs if r.kind == "link"]
    if corrected and linked:  # the user corrects one link: a related rejection becomes "no lasting rule", an unrelated one becomes about C5
        first = rng.choice(linked)
        recs.append(Rec(f"c:{first.key}", "link", first.case, ids=("C5",) if "none" in first.ids else ("none",), needs=(first.key,)))
    return recs


def worlds(recs: Sequence[Rec], order: Sequence[Rec]) -> Watching:
    """The files after ``order``'s records, stamped in that order (ticks 1000 on), over the deliveries made up front."""
    w = world()
    w.case("c1", 20, 21)
    w.case("c2", 22, 23)
    w.case("c3", 24, 25)
    w.case("c4", 26, 27)
    w.case("cb", 19, 20, status="blocked")
    notes: dict[str, Message] = {}
    rejections = [r.key for r in order if r.kind == "verdict" and r.verdict == "reject"]
    for i, rec in enumerate(order):
        tick = 1000 + i
        if rec.kind == "verdict":
            notes[rec.key] = w.bag.verdict(w.tasks[rec.case], tick, rec.verdict)
        elif rec.kind == "relayed":
            w.bag.verdict(w.tasks[rec.case], tick, rec.verdict, source="relayed")
        elif rec.kind == "link":
            ids = tuple(f"R{rejections.index(x[1:]) + 2}" if x.startswith("@") else x for x in rec.ids)
            w.bag.link(notes[rec.case], tick, *ids)
        else:
            w.contracts.append(contract(2, ACCEPTANCE, tick, answers=notes[rec.case].id, about="C5"))
    return w


def label_of(w: Watching) -> str:
    return label(w.states()["P2"])


def admissible(recs: Sequence[Rec]) -> list[tuple[Rec, ...]]:
    """The orders that keep every record after the ones it needs."""
    found = []
    for order in permutations(recs):
        seen: set[str] = set()
        for rec in order:
            if not set(rec.needs) <= seen:
                break
            seen.add(rec.key)
        else:
            found.append(order)
    return found


def sequences(recs: Sequence[Rec]) -> list[tuple[tuple[Rec, ...], list[str]]]:
    """Every admissible order with the state read after each of its records (the prefixes shared by orders are read once)."""
    memo: dict[tuple[str, ...], str] = {}

    def read(prefix: tuple[Rec, ...]) -> str:
        key = tuple(r.key for r in prefix)
        if key not in memo:
            memo[key] = label_of(worlds(recs, prefix))
        return memo[key]

    return [(order, [read(order[:n]) for n in range(len(order) + 1)]) for order in admissible(recs)]


@lru_cache(maxsize=None)
def runs(seed: int, mode: str = "") -> tuple[tuple[tuple[Rec, ...], list[str]], ...]:
    """The watch of a seed (``mode``: "", "corrected" or "b1") with every admissible order and its states, read once for all the tests."""
    return tuple(sequences(scenario(seed, b1=mode == "b1", corrected=mode == "corrected")))


def violations(states: Sequence[str]) -> list[int]:
    """The positions where the state moves outside ``PATHS``."""
    return [i + 1 for i, (before, after) in enumerate(zip(states, states[1:])) if after not in PATHS[before]]


def test_every_admissible_order_moves_only_along_the_paths() -> None:
    for seed in SEEDS:
        assert len(scenario(seed)) <= MAX_RECORDS
        for order, states in runs(seed):
            assert violations(states) == [], (seed, [r.key for r in order], states)


def test_the_final_state_equals_the_derivation_from_scratch() -> None:
    """The same files read again, the cases and the results listed in another order, give the state the last record left."""
    for seed in SEEDS:
        recs = scenario(seed)
        for order, states in runs(seed)[:60]:
            w = worlds(recs, order)
            cases, results = w.bag.cases(), w.bag.results()
            stored = [(c.version, c.defined_by or "", c.acceptance) for c in w.contracts]
            criteria = number_criteria(stored, {c.version: (c.answers, c.initiated == "user") for c in w.contracts})
            again = watch_states(w.versions, cases[::-1], dict(reversed(list(results.items()))), criteria, w.contracts[::-1])
            assert label(next(i for i in again if i.id == "P2")) == states[-1], (seed, [r.key for r in order])


def test_one_corrected_link_is_the_only_move_outside_the_paths() -> None:
    """The one exception to the monotonicity property (8.2): a corrected link can unrelate a related rejection or relate an unrelated one."""
    outside: set[tuple[str, str]] = set()
    for seed in CORRECTED_SEEDS:
        fix = next(r for r in scenario(seed, corrected=True) if r.key.startswith("c:"))  # every seed holds one
        for order, states in runs(seed, "corrected"):
            position = [r.key for r in order].index(fix.key) + 1
            assert set(violations(states)) <= {position}, (seed, [r.key for r in order], states)
            outside |= {(before, after) for before, after in zip(states, states[1:]) if after not in PATHS[before]}
    assert {("kept", "warning"), ("warning", "new")} <= outside  # the exception does happen, and only there


def test_a_second_related_rejection_recorded_after_d_retires_in_every_order() -> None:
    """B1: R2 (c2's) warns P2 inside the window and R3 (c4's, after E) is read over the warned window, whatever the order."""
    for seed in B1_SEEDS:
        for order, states in runs(seed, "b1"):
            assert states[-1] == "due" and violations(states) == [], (seed, [r.key for r in order], states)


def test_the_generated_watches_hold_late_records_and_end_in_every_state() -> None:
    """The seeds are not all alike: some hold a rejection of the later delivery (c4) or of the blocked result, a second verdict or an answering
    version, and the watches end ``new``, ``kept``, ``warning`` and ``due``, in different orders of the same records."""
    keys = {r.key for seed in SEEDS for r in scenario(seed)}
    assert {"x:c4", "x:cb", "s:c2", "rl:c3"} <= keys and any(k.startswith("a:") for k in keys)
    assert {states[-1] for seed in SEEDS for _, states in runs(seed)} == {"new", "kept", "warning", "due"}


# ------------------------------------------------------------------------------------------- 18.4.1: the rows and moments, pre-registered

A, B = "P2", "P3"  # the items of the scripted stream: A (WHY R1; C9) and B (WHY R2; C10)


def both(stream: Stream) -> tuple[str, str]:
    a, b = stream.states()
    return label(a), label(b)


def steps(build: Callable[[Stream, Sequence[str]], None], order: Sequence[str]) -> list[tuple[str, str]]:
    """The states of A and B after each prefix of ``order``: ``build`` makes the stream and records the first ``n`` names of the order."""
    out = []
    for n in range(len(order) + 1):
        stream = Stream()
        build(stream, order[:n])
        out.append(both(stream))
    return out


def upto_memo4(stream: Stream) -> Message:
    """Memos 1, 2 and 3 as delivered, memo 4 delivered (ask 150, done 151); memo 3's verdict and memo 4's rejection are the moment's."""
    stream.memo1()
    stream.memo2()
    stream.w.case("m3", 140, 141)
    stream.w.case("m4", 150, 151)
    return stream.w.tasks["m3"]


def check_o1() -> None:
    """O1: memo 3's late verdict against R3 (memo 4's rejection) and R3's answer. A is ``new`` until the later of memo 3's human accept and R3's
    answer, then ``kept``, in every order; B is ``warning`` from R3's answer on (its D waits for memo 5)."""
    orders = (("accept", "reject", "answer"), ("reject", "accept", "answer"), ("reject", "relayed", "answer", "accept"))
    for order in orders:
        def build(stream: Stream, done: Sequence[str]) -> None:
            m3 = upto_memo4(stream)
            for i, name in enumerate(done):
                tick = 200 + i
                if name == "accept":
                    stream.w.bag.verdict(m3, tick, "accept")
                elif name == "relayed":
                    stream.w.bag.verdict(m3, tick, "accept", source="relayed")
                elif name == "reject":
                    stream.w.notes["m4"] = stream.w.bag.verdict(stream.w.tasks["m4"], tick, "reject")
                else:
                    stream.answer("m4", tick, [INITIALS], [FULL_NAMES], "C10", ["C11"])

        seen = steps(build, order)
        for n, (a, b) in enumerate(seen):
            recorded = set(order[:n])
            assert a == ("kept" if {"accept", "answer"} <= recorded else "new"), (order, n, a)
            assert b == ("warning" if "answer" in recorded else "new"), (order, n, b)


def check_o2() -> None:
    """O2: R3's answer as a contract version removing C10 and adding C11, or as a link alone naming C10: B is ``warning`` at that call either way."""
    for with_version in (True, False):
        stream = Stream()
        m3 = upto_memo4(stream)
        stream.w.bag.verdict(m3, 153, "accept")
        stream.w.notes["m4"] = stream.w.bag.verdict(stream.w.tasks["m4"], 152, "reject")
        assert both(stream) == ("new", "new")  # R3 is pending
        if with_version:
            stream.answer("m4", 160, [INITIALS], [FULL_NAMES], "C10", ["C11"])
        else:
            stream.answer("m4", 160, [], [], "C10", ["C10"], contract_version=False)
        assert both(stream) == ("kept", "warning"), with_version


def memo5_flow(stream: Stream, *, relayed_first: bool = False, superseded: bool = False) -> None:
    """Memo 5 after R3's answer, its rejection (R4) and the answer (C12 added, C11 removed)."""
    m5 = stream.w.case("m5", 170, 171)
    if relayed_first:
        stream.w.bag.verdict(m5, 172, "reject", source="relayed")
    target = m5
    if superseded:
        target = stream.w.case("m5r", 172, 173, revises=m5, asked_by="relayed")
    stream.w.notes["m5"] = stream.w.bag.verdict(target, 174, "reject")
    stream.answer("m5", 180, [FULL_NAMES], [NOTE], "C11", ["C12"])


def through_memo4(stream: Stream) -> None:
    m3 = upto_memo4(stream)
    stream.w.bag.verdict(m3, 153, "accept")
    stream.w.notes["m4"] = stream.w.bag.verdict(stream.w.tasks["m4"], 152, "reject")
    stream.answer("m4", 160, [INITIALS], [FULL_NAMES], "C10", ["C11"])


def check_o3_o4() -> None:
    """O3: a relayed rejection of memo 5 before Lena's, or hers alone; O4: memo 5's first delivery superseded before her verdict. B is retired (due) at
    R4's answer; the user's judged delivery is hers in every case."""
    for flags in ({}, {"relayed_first": True}, {"superseded": True}, {"relayed_first": True, "superseded": True}):
        stream = Stream()
        through_memo4(stream)
        assert both(stream) == ("kept", "warning")
        memo5_flow(stream, **flags)
        a, b = stream.states()
        assert (label(a), label(b), b.related) == ("kept", "due", ("R3", "R4")), flags


def check_o5() -> None:
    """O5: memo 3's human accept recorded after R4 (root passed P2-UNRATED with a relayed verdict). R4, recorded before D, is in A's window and
    unrelated to A: A is ``kept`` at memo 3's accept (at R4's answer when the accept came later than the answer is not due); B is due at R4's answer."""
    for accept in (185, 175):
        stream = Stream()
        stream.memo1()
        stream.memo2()
        m3 = stream.w.case("m3", 140, 141)
        stream.w.case("m4", 150, 151)
        stream.w.bag.verdict(m3, 153, "accept", source="relayed")
        stream.w.notes["m4"] = stream.w.bag.verdict(stream.w.tasks["m4"], 152, "reject")
        stream.answer("m4", 160, [INITIALS], [FULL_NAMES], "C10", ["C11"])
        assert both(stream)[0] == "new"  # memo 3 has no counted verdict: waiting
        memo5_flow(stream)
        stream.w.bag.verdict(m3, accept, "accept")
        assert both(stream) == ("kept", "due"), accept


def check_o6() -> None:
    """O6: memo 4's rework accept recorded before, between or after memo 5's request and R4's answer moves no state of A or B."""
    for accept in (156, 175, 185):
        stream = Stream()
        through_memo4(stream)
        stream.w.case("m4h", 154, 155, verdict=(accept, "accept"), revises=stream.w.tasks["m4"], asked_by="human")
        memo5_flow(stream)
        assert both(stream) == ("kept", "due"), accept


def check_o7() -> None:
    """O7: B added in memo 3's run (the base case), in memo 4's run before its first delivery, and after it."""
    for live, expected in (((130, 0), ("kept", "due")), ((150, 500000), ("kept", "due")), ((151, 500000), ("kept", "warning"))):
        stream = Stream()
        stream.memo1()
        stream.memo2(live=live)
        m3 = stream.w.case("m3", 140, 141)
        stream.w.case("m4", 150, 151)
        stream.w.bag.verdict(m3, 153, "accept")
        stream.w.notes["m4"] = stream.w.bag.verdict(stream.w.tasks["m4"], 152, "reject")
        stream.answer("m4", 160, [INITIALS], [FULL_NAMES], "C10", ["C11"])
        memo5_flow(stream)
        stream.w.case("m6", 190, 191, verdict=(192, "accept"))
        a, b = stream.states()
        assert (label(a), label(b)) == expected, live
        if live == (151, 500000):  # R3's result predates B: only R4 relates, there is no second related rejection to read
            assert b.related == ("R4",)


def check_o8() -> None:
    """O8: B's owner edits B (a gated change) after R3: B stays ``warning`` (D4) and R4 retires it, read over the edit's own window too."""
    stream = Stream()
    through_memo4(stream)
    stream.item(165, rule("P3", "always", "write the owners as initials only, never in full", why=("R2", "C10")), op="edit")
    assert stream.states()[1].state == "warning" and stream.states()[1].related == ("R3",)
    memo5_flow(stream)
    assert both(stream) == ("kept", "due")


def check_o9() -> None:
    """O9: B's owner retires B after R3 (its coverage is empty: C10 is removed). Then a re-add, a restore or a gated edit of another live item into its
    text continues the watch (carried) and R4 retires the carrying item; with none of them B stays ``retired``."""
    words = "write owners as initials only"
    variants = {
        "none": None, "re-add": rule("P4", "always", words, why=("R2", "C10")), "restore": rule("P3", "always", words, why=("R2", "C10")),
        "edit": rule("P2", "always", words, why=("R2", "C10")),  # A edited into B's words, on the evidence B rested on
    }
    for name, new in variants.items():
        stream = Stream()
        through_memo4(stream)
        stream.retire(165, "P3")
        assert stream.states()[1].state == "retired"
        if new is not None:
            stream.item(170, new, op="restore" if name == "restore" else "edit" if name == "edit" else "add", admitted="c")
        memo5_flow(stream)
        found = stream.w.states()
        carrier = found[new.id] if new is not None else found["P3"]
        if new is None:
            assert (carrier.state, carrier.related) == ("retired", ("R3",)), name  # vacuous: nothing continues the watch
        else:
            assert (carrier.carried, carrier.related, carrier.retire_due) == ("P3", ("R3", "R4"), True), name
        if name == "edit":
            assert found["P2"].carried == "P3"


def check_o10() -> None:
    """O10: memo 2's change removed C6 (adding C10), memo 4's answer brings C6's exact text back (removing C10); B is ``warning`` at R3's answer and
    retired (due) at R4's, with the new "full names" text (a) or with C6's text (b)."""
    for variant in ("a", "b"):
        stream = Stream()
        stream.memo1()
        stream.w.case("m2", 120, 121, verdict=(122, "reject"))
        stream.answer("m2", 123, ["owners"], [INITIALS], "C6", ["C10"])
        stream.w.case("m2h", 124, 125, verdict=(126, "accept"), revises=stream.w.tasks["m2"], asked_by="human")
        stream.item(130, rule("P3", "always", "write owners as initials only", why=("R2", "C10")))
        m3 = stream.w.case("m3", 140, 141)
        stream.w.case("m4", 150, 151)
        stream.w.bag.verdict(m3, 153, "accept")
        stream.w.notes["m4"] = stream.w.bag.verdict(stream.w.tasks["m4"], 152, "reject")
        added, ids = (["owners"], ["C6"]) if variant == "b" else ([FULL_NAMES], ["C11"])
        stream.answer("m4", 160, [INITIALS], added, "C10", ids)
        assert both(stream) == ("kept", "warning"), variant
        m5 = stream.w.case("m5", 170, 171)
        stream.w.notes["m5"] = stream.w.bag.verdict(m5, 172, "reject")
        stream.answer("m5", 180, added, [NOTE], ids[0], ["C12"])
        assert both(stream) == ("kept", "due"), variant


def test_the_constructed_rows_xiii_to_xxv_and_moments_o1_to_o10_give_their_pre_registered_states() -> None:
    from . import test_watch, test_watch_subjects

    for name in (
        "test_row_xiii_a_later_case_rejected_and_linked_before_the_kth_verdict_stays_warning_after_it",
        "test_row_xiv_the_same_rejection_recorded_after_the_kth_verdict_is_outside_the_window",
        "test_row_xv_a_relayed_verdict_before_the_link_and_the_human_verdict_after_it_stays_warning",
        "test_row_xvi_a_rejection_recorded_after_k_leaves_kept",
        "test_row_xvii_a_pending_rejection_at_d_then_a_related_one_is_warning",
        "test_row_xix_a_corrected_link_after_k_is_warning_and_a_second_the_retire",
        "test_row_xx_a_second_related_rejection_of_a_later_delivery_after_d_is_due_in_every_order",
        "test_row_xxi_a_gated_edit_of_another_item_into_a_warned_retired_text_is_carried_with_its_own_rejections",
    ):
        getattr(test_watch, name)()
    for name in (
        "test_same_as_an_unanswered_rejection_is_pending_until_it_is_answered",  # row xviii's subjects
        "test_a_v1_text_removed_then_re_added_has_the_lineage_of_the_re_adding_answer",  # xxiii
        "test_a_rejection_answered_before_the_re_add_keeps_its_subjects",  # xxiv
        "test_a_lineage_cycle_ends_with_each_id_once",  # xxv
    ):
        getattr(test_watch_subjects, name)()
    for check in (check_o1, check_o2, check_o3_o4, check_o5, check_o6, check_o7, check_o8, check_o9, check_o10):
        check()
