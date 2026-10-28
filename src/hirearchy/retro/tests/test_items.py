"""Items (design 4.5a): the candidates of the signals become at most three numbered items. The order is total; a key already asked is suppressed until new evidence; a clarify is asked
once per wording; a cause lapses at most twice; an item not taken lapses at the next recorded brief."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from hirearchy.services import line_key
from hirearchy.retro import BriefRecord, Item, RecordedItem, retro_thresholds
from hirearchy.retro._items import EffectFacts, fates, select, taken_by, to_record

T0 = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)


def cand(kind: str, key: str, evidence: tuple[str, ...] = ("M1",), weight: int = 1, rung: int = 2, oldest: str = "M1", effect: dict[str, str] | None = None) -> Item:
    return Item(kind, key, evidence, weight, rung, oldest=oldest, effect=effect or {})


def brief(n: int, *items: RecordedItem) -> BriefRecord:
    return BriefRecord(f"B{n}", T0 + timedelta(days=n), None, "mcp", items)


def recorded(n: int, kind: str, key: str, evidence: tuple[str, ...] = ("M1",), lapsed: int = 0, **effect: str) -> RecordedItem:
    return RecordedItem(n, kind, key, evidence, effect, lapsed)


def keys(found: tuple[Item, ...]) -> list[str]:
    return [i.key for i in found]


def pick(candidates: list[Item], records: tuple[BriefRecord, ...] = (), asked: frozenset[str] = frozenset(), taken: frozenset[str] = frozenset(), cap: int = 3):  # type: ignore[no-untyped-def]
    return select(candidates, records, asked, taken, cap)


def test_the_order_is_weight_rung_oldest_evidence_kind_then_key() -> None:
    found = pick([
        cand("retire", "retire|a", weight=1, rung=7), cand("service", "service|b", weight=3), cand("checker-add", "checker-add|c", weight=3, rung=4),
        cand("answer", "answer|d", weight=3, rung=2, oldest="M9"), cand("cause", "cause|e", weight=3, rung=2, oldest="M2"), cand("answer", "answer|f", weight=3, rung=2, oldest="M2"),
    ], cap=9)
    assert keys(found.items) == ["service|b", "answer|f", "cause|e", "answer|d", "checker-add|c", "retire|a"]
    # weight 3 first; then rung 2 (cheaper) before rung 4; among rung 2 the oldest evidence (M1 < M2 < M9), then the kind order (answer before cause), then the key
    assert pick([cand("reclaim", "reclaim|a", weight=0, rung=0), cand("clarify", "clarify|b", weight=0, rung=1)]).items[0].key == "reclaim|a"  # no rung: cheapest
    same = [cand("service", "service|z", oldest="M1"), cand("service", "service|a", oldest="M1")]
    assert keys(pick(same).items) == keys(pick(list(reversed(same))).items) == ["service|a", "service|z"]  # a total order: two runs give the same brief


def test_at_most_three_items_and_a_value_above_three_keeps_three_with_a_note() -> None:
    many = [cand("service", f"service|{n}", weight=9 - n, oldest=f"M{n}") for n in range(5)]
    thresholds, notes = retro_thresholds({"retro": {"items": 7}})
    found = pick(many, cap=thresholds.items)
    assert [i.n for i in found.items] == [1, 2, 3] and keys(found.held_back) == ["service|3", "service|4"]
    assert notes == ("retro.items in ORG.md is above 3: 3 is used (a brief has at most 3 items).",)


def test_items_1_or_2_from_org_md() -> None:
    many = [cand("service", f"service|{n}", weight=9 - n) for n in range(4)]
    for cap in (1, 2):
        thresholds, notes = retro_thresholds({"retro": {"items": cap}})
        found = pick(many, cap=thresholds.items)
        assert len(found.items) == cap and len(found.held_back) == 4 - cap and notes == ()


def test_a_key_in_asked_is_suppressed_until_new_evidence() -> None:
    last = brief(1, recorded(1, "service", "service|lead|M1", ("M1", "M2", "M3")))
    candidates = [cand("service", "service|lead|M1", ("M1", "M2", "M3"))]
    assert pick(candidates, (last,), frozenset({"service|lead|M1"})).items == ()
    assert keys(pick([cand("service", "service|lead|M1", ("M1", "M2", "M3", "M4"))], (last,), frozenset({"service|lead|M1"})).items) == ["service|lead|M1"]  # a new case brings it back
    assert pick(candidates, (), frozenset({"service|lead|M1"})).items == ()  # asked longer ago than the records reach: no evidence to compare, so it stays suppressed
    assert keys(pick(candidates).items) == ["service|lead|M1"]  # never asked
    assert pick(candidates, (last,), taken=frozenset({"service|lead|M1"})).items == ()  # its effect is already seen


def test_clarify_is_asked_once_per_wording() -> None:
    last = brief(1, recorded(1, "clarify", "clarify|memos|C1|x", ("memos/C1",)))
    again = cand("clarify", "clarify|memos|C1|x", ("memos/C1", "memos/C1 again"))
    assert pick([again], (last,), frozenset({"clarify|memos|C1|x"})).items == ()  # new evidence does not bring it back
    assert keys(pick([cand("clarify", "clarify|memos|C1|y", ("memos/C1",))], (last,), frozenset({"clarify|memos|C1|x"})).items) == ["clarify|memos|C1|y"]  # another wording is another key


def test_cause_lapses_at_most_twice() -> None:
    cause = cand("cause", "cause|R3", ("R3",), rung=1)
    first = brief(1, recorded(1, "cause", "cause|R3", ("R3",), lapsed=0))
    second = brief(2, recorded(1, "cause", "cause|R3", ("R3",), lapsed=1))
    asked = frozenset({"cause|R3"})
    assert keys(pick([cause], (first,), asked).items) == ["cause|R3"]  # lapsed once: asked again
    assert pick([cause], (first, second), asked).items == ()  # lapsed twice: it stays a line of D4, not an item
    assert pick([cause], (first,), asked, taken=frozenset({"cause|R3"})).items == ()
    again = pick([cause], (first,), asked).items
    assert [i.n for i in again] == [1] and to_record(again, (first,), frozenset())[0].lapsed == 1  # the record says it lapsed once before


def test_an_item_not_taken_lapses_at_the_next_recorded_brief_and_returns_only_with_new_evidence() -> None:
    last = brief(2, recorded(1, "service", "service|lead|M1", ("M1", "M2", "M3")), recorded(2, "retire", "retire|ceo/x", ("ceo/x",), lapsed=0, agent="ceo/x"))
    found = pick([cand("service", "service|lead|M1", ("M1", "M2", "M3"))], (last,), frozenset({"service|lead|M1", "retire|ceo/x"}), taken=frozenset({"retire|ceo/x"}))
    assert found.items == () and found.lapsed == ("service|lead|M1",)  # not taken: it lapses; the retire was taken: it does not
    assert [(f.id, f.state) for f in fates(last, EffectFacts(retired=frozenset({"ceo/x"})), recorded=True)] == [("B2.1", "lapsed"), ("B2.2", "taken")]
    assert [(f.id, f.state) for f in fates(last, EffectFacts(retired=frozenset({"ceo/x"})), recorded=False)] == [("B2.1", "open"), ("B2.2", "taken")]
    assert fates(None, EffectFacts(), recorded=True) == ()


@pytest.mark.parametrize(
    ("kind", "effect", "facts", "seen"),
    [
        ("service", {"service": "ceo/list"}, EffectFacts(services=frozenset({"ceo/list"})), "ceo/list defined"),
        ("checker-add", {"owner": "ceo"}, EffectFacts(checkers=frozenset({"ceo"})), "a checker joined ceo's team"),
        ("checker-fix", {"agent": "ceo/c", "line": "Check C4 item by item."}, EffectFacts(lines=frozenset({f"ceo/c|{line_key('Check C4 item by item.')}"})), "the line is in ceo/c's charter"),
        ("worker", {"lead": "ceo"}, EffectFacts(workers=frozenset({"ceo"})), "a worker joined ceo's team"),
        ("retire", {"agent": "ceo/x"}, EffectFacts(retired=frozenset({"ceo/x"})), "ceo/x retired"),
        ("reclaim", {"agent": "ceo"}, EffectFacts(reclaimed=frozenset({"ceo"})), "ceo's runs came back"),
        ("clarify", {"service": "memos", "criterion": "C1"}, EffectFacts(clarified=frozenset({"memos/C1"})), "memos C1 was settled"),
        ("cause", {"rejection": "R3"}, EffectFacts(answered=frozenset({"R3"})), "R3 was answered"),
        ("answer", {"rejection": "R3"}, EffectFacts(answered=frozenset({"R3"})), "R3 was answered"),
    ],
)
def test_each_kinds_effect_marks_it_taken(kind: str, effect: dict[str, str], facts: EffectFacts, seen: str) -> None:
    item = RecordedItem(1, kind, f"{kind}|k", (), effect)
    assert taken_by(item, facts) == seen and taken_by(item, EffectFacts()) == ""
