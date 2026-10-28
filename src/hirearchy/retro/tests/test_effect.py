"""Did past changes hold (design 4.4): the outcome of a change is read from the cases where it was exercised and the rejections that came after it. Pure; only the user's own
(human-tier) verdicts count, and no text says that a change helped."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import hirearchy.retro
from hirearchy.retro._effect import Evaluated, evaluate, listed
from hirearchy.retro._readings import d7_held
from hirearchy.retro._views import Occasion, Tracked, WatchState

T0 = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)


def at(days: int) -> datetime:
    return T0 + timedelta(days=days)


def cases(n: int, tier: str = "human") -> tuple[Occasion, ...]:
    return tuple(Occasion(f"M{k}", "", at(k), tier) for k in range(1, n + 1))


def tracked(kind: str, text: str, **fields: object) -> Tracked:
    return Tracked(text, kind, at(0), True, **fields)  # type: ignore[arg-type]


# ------------------------------------------------------------------------------ one row per change kind


def test_a_contract_amendment_holds_when_its_target_is_not_rejected_in_the_window() -> None:
    held = evaluate(tracked("amendment", "memos v3 adds C9", exercised=cases(3)), 3)
    assert (held.text, held.outcome, held.final) == ("memos v3 adds C9", "not recurred in 3 cases where it was exercised", True)
    assert held.changed == at(3)  # the case that reached the window
    recurred = evaluate(tracked("amendment", "memos v3 adds C9", exercised=cases(2), recurred=(Occasion("M4", "R6", at(4)),)), 3)
    assert recurred.outcome == "recurred in case M4 (R6)" and recurred.changed == at(4)


def test_a_playbook_item_reads_phase_1s_watch() -> None:
    warned = evaluate(tracked("playbook", "memos P3 (v6)", watch=WatchState("warning", 3, 1, ("R5", "R6"))), 3)
    assert warned.outcome == "recurred: warning (R5, R6)" and warned.final
    retired = evaluate(tracked("playbook", "memos P3 (v6)", watch=WatchState("retired", 3, 3, ("R5",))), 3)
    assert retired.outcome == "recurred: retired (R5)"
    kept = evaluate(tracked("playbook", "memos P3 (v6)", watch=WatchState("kept", 4, 4, ())), 3)
    assert kept.outcome == "not recurred in 4 cases where it was exercised"  # the item's own k, not the window
    new = evaluate(tracked("playbook", "memos P3 (v6)", watch=WatchState("new", 4, 2, ())), 3)
    assert new.outcome == "INCONCLUSIVE (2 of 4 exercised cases)" and not new.final


def test_a_charter_edit_reads_the_target_of_the_item_it_is_the_effect_of() -> None:
    held = evaluate(tracked("charter", "charter of ceo/checker (B1.2)", exercised=cases(4)), 3)
    assert held.outcome == "not recurred in 4 cases where it was exercised"
    assert evaluate(Tracked("charter of ceo/x edited by ceo", "charter", at(0), False), 3).outcome == "no target recorded: not evaluated"


def test_a_structural_change_reads_the_recurrence_of_its_target() -> None:
    service = evaluate(tracked("structural", "service ceo/list (B1.1)", exercised=cases(1), recurred=(Occasion("M9", "", at(9)),)), 3)
    assert service.outcome == "recurred in case M9"  # a later one-off task of the same shape: no rejection id
    checker = evaluate(tracked("structural", "checker ceo/checker (B1.2)", exercised=cases(2)), 3)
    assert checker.outcome == "INCONCLUSIVE (2 of 3 exercised cases)"


# ------------------------------------------------------------------------------ the order of the outcomes


def test_recurred_comes_first() -> None:
    both = tracked("amendment", "t", exercised=cases(5), recurred=(Occasion("M7", "R9", at(7)), Occasion("M8", "R10", at(8))))
    assert evaluate(both, 3).outcome == "recurred in case M7 (R9)"  # the first later related rejection, though the window was reached


def test_not_recurred_in_n_cases_from_the_window() -> None:
    assert evaluate(tracked("amendment", "t", exercised=cases(3)), 3).outcome == "not recurred in 3 cases where it was exercised"
    assert evaluate(tracked("amendment", "t", exercised=cases(5)), 3).outcome == "not recurred in 5 cases where it was exercised"
    assert evaluate(tracked("amendment", "t", exercised=cases(2)), 2).outcome == "not recurred in 2 cases where it was exercised"  # the window comes from the thresholds


def test_inconclusive_below_the_window() -> None:
    held = evaluate(tracked("amendment", "t", exercised=cases(2)), 3)
    assert held.outcome == "INCONCLUSIVE (2 of 3 exercised cases)" and not held.final and held.changed is None
    assert evaluate(tracked("amendment", "t"), 3).outcome == "INCONCLUSIVE (0 of 3 exercised cases)"


def test_no_target_recorded_is_not_evaluated() -> None:
    nothing = evaluate(Tracked("a hire inside the envelope", "structural", at(0), False, exercised=cases(5), recurred=cases(1)), 3)
    assert (nothing.outcome, nothing.final, nothing.changed) == ("no target recorded: not evaluated", True, None)


def test_relayed_and_agent_verdicts_weigh_0() -> None:
    mixed = tracked("amendment", "t", exercised=cases(2) + cases(5, "relayed")[2:] + cases(1, "agent"), recurred=(Occasion("M8", "R2", at(8), "relayed"), Occasion("M9", "R3", at(9), "agent")))
    assert evaluate(mixed, 3).outcome == "INCONCLUSIVE (2 of 3 exercised cases)"  # three non-human cases and two non-human rejections count for nothing
    human = evaluate(tracked("amendment", "t", exercised=cases(3), recurred=(Occasion("M8", "R2", at(8), "relayed"),)), 3)
    assert human.outcome == "not recurred in 3 cases where it was exercised"


# ------------------------------------------------------------------------------ which changes are listed


def test_inconclusive_changes_are_carried_for_carry_briefs() -> None:
    since, carry_since = at(20), at(5)
    new = Evaluated("new", "amendment", at(21), "INCONCLUSIVE (0 of 3 exercised cases)", False, None)
    reached = Evaluated("reached", "amendment", at(10), "not recurred in 3 cases where it was exercised", True, at(22))
    recurred = Evaluated("recurred", "amendment", at(2), "recurred in case M4 (R6)", True, at(21))
    old_settled = Evaluated("old settled", "amendment", at(10), "not recurred in 3 cases where it was exercised", True, at(12))
    carried = Evaluated("carried", "amendment", at(8), "INCONCLUSIVE (1 of 3 exercised cases)", False, None)
    too_old = Evaluated("too old", "amendment", at(3), "INCONCLUSIVE (1 of 3 exercised cases)", False, None)
    untargeted = Evaluated("untargeted", "structural", at(9), "no target recorded: not evaluated", True, None)
    found = listed([old_settled, too_old, untargeted, carried, recurred, reached, new], since, carry_since)
    assert [e.text for e in found] == ["recurred", "carried", "reached", "new"]  # oldest first; a settled or untargeted old change and a carry that went out of reach are not
    assert [e.text for e in listed([carried, too_old], since, None)] == ["too old", "carried"]  # with fewer than `carry` briefs: since the organization started


def test_d7_lists_one_line_per_change() -> None:
    rows = [Evaluated("memos v3 adds C9", "amendment", at(1), "recurred in case M4 (R6)", True, at(4)), Evaluated("ceo/x hired", "structural", at(2), "no target recorded: not evaluated", True, None)]
    section = d7_held(rows, [])
    assert section.key == "d7" and section.heading == "Did past changes hold"
    assert section.block == section.details == ("- memos v3 adds C9: recurred in case M4 (R6)", "- ceo/x hired: no target recorded: not evaluated")
    assert d7_held([], []).details == ("- none",) and section.counts == (("changes", 2), ("recurred", 1), ("not_evaluated", 1))


def test_no_text_says_it_helped() -> None:
    package = Path(hirearchy.retro.__file__).resolve().parent
    words = ("helped", "improved", "worked", "effective", "success", "better")
    found = [
        f"{name}: {node.value!r}" for name in ("_effect.py", "_readings.py") for node in ast.walk(ast.parse((package / name).read_text(encoding="utf-8")))
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and any(w in node.value.lower() for w in words)
    ]
    assert found == []
