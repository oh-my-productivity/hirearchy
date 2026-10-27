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
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations

from hirearchy.kernel import Message
from hirearchy.reflection._watch import watch_states
from hirearchy.services import ItemWatch, number_criteria

from ._watch_kit import Watching, contract, world

SEEDS = (33, 53, 20, 21, 58, 81, 15, 25)  # the generated watches: 60 to 840 admissible orders each, 2 to 7 records
CORRECTED_SEEDS = (5, 19, 64, 90)  # watches with one corrected link inserted
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
    corrected = 0
    for seed in CORRECTED_SEEDS:
        recs = scenario(seed, corrected=True)
        fix = next((r for r in recs if r.key.startswith("c:")), None)
        if fix is None:
            continue
        corrected += 1
        for order, states in runs(seed, "corrected"):
            position = [r.key for r in order].index(fix.key) + 1
            assert set(violations(states)) <= {position}, (seed, [r.key for r in order], states)
    assert corrected >= 2


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
