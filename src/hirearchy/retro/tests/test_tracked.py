"""D7 weighs the charter edits and the structural changes too (design 4.4, rows 3 and 4): a change that is the effect of an item is read by its target, any other reads
``no target recorded: not evaluated``. The facts are scripted here; ``tests/e2e/test_org_growth_2.py`` reads them from a real organization."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hirearchy.retro import BriefRecord, RecordedItem
from hirearchy.retro._changes import ChangeFacts
from hirearchy.retro._effect import NOT_EVALUATED, evaluate
from hirearchy.retro._facts import Facts
from hirearchy.retro._ports import CharterPair, CharterVersions, KeyChange
from hirearchy.retro._tracked import structural_tracked
from hirearchy.retro._views import AgentFact, EffectFacts, Occasion, OneOffCase, Rejection, ServiceFact

START = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)
LIMITS = "- Your hiring limits were set by the user's change: up to 3 direct reports; may hire: yes. [change cafe00000001]"
LINE = "Check C4 of memos item by item on every request: Every claim names its source."


def at(minutes: int) -> datetime:
    return START + timedelta(minutes=minutes)


def held(*items: RecordedItem) -> tuple[BriefRecord, ...]:
    return (BriefRecord("B1", at(0), None, "mcp", items),)


def checker_add() -> RecordedItem:
    return RecordedItem(2, "checker-add", "checker-add|memos|C4", ("M1", "M2", "M3"), {"owner": "ceo"})


def agent(addr: str, minutes: int, approved_in: str, verifier: bool = False, hired_by: str = "root") -> AgentFact:
    return AgentFact(addr, at(minutes), hired_by, approved_in, "verifier" if verifier else "author", False, verifier)


def failing(case: str, minutes: int, *classes: str) -> Rejection:
    return Rejection(case, at(minutes), tuple(frozenset({c}) for c in classes))


def memos(*rejections: Rejection) -> dict[str, tuple[Rejection, ...]]:
    return {"memos": rejections}


def weigh(facts: Facts, briefs: tuple[BriefRecord, ...] = ()) -> list[tuple[str, str, str]]:
    return [(t.text, t.kind, evaluate(t, 3).outcome) for t in structural_tracked(facts, briefs)]


def judged(*minutes: int) -> dict[str, tuple[Occasion, ...]]:
    return {"memos": tuple(Occasion(f"M{n}", "", at(m)) for n, m in enumerate(minutes, start=4))}


def test_a_checker_the_user_took_is_inconclusive_below_the_window_then_not_recurred() -> None:
    changes = ChangeFacts(agents=(agent("ceo/c4-checker", 10, "change cafe00000001", True),))
    facts = Facts(changes=changes, judged=judged(5, 11, 12))  # one case before the change, two after it
    assert weigh(facts, held(checker_add())) == [("agent ceo/c4-checker added (2026-11-02), item B1.2", "structural", "INCONCLUSIVE (2 of 3 exercised cases)")]
    more = Facts(changes=changes, judged=judged(5, 11, 12, 13))
    assert weigh(more, held(checker_add()))[0][2] == "not recurred in 3 cases where it was exercised"


def test_a_later_rejection_on_the_criterion_s_class_is_a_recurrence_and_an_earlier_one_is_not() -> None:
    changes = ChangeFacts(agents=(agent("ceo/c4-checker", 10, "change cafe00000001", True),))
    again = Facts(changes=changes, judged=judged(11), rejected=memos(failing("M1", 2, "C4"), failing("M5", 11, "C4")))
    assert weigh(again, held(checker_add()))[0][2] == "recurred in case M5"
    other = Facts(changes=changes, judged=judged(11), rejected=memos(failing("M1", 2, "C4"), failing("M6", 12, "C9")))
    assert weigh(other, held(checker_add()))[0][2] == "INCONCLUSIVE (1 of 3 exercised cases)"


def test_a_recurrence_is_remembered_after_ten_accepted_cases_follow_it() -> None:
    changes = ChangeFacts(agents=(agent("ceo/c4-checker", 10, "change cafe00000001", True),))
    accepted = {"memos": tuple(Occasion(f"M{n}", "", at(12 + n)) for n in range(5, 16))}  # eleven judged cases after the change, ten of them after the rejection
    facts = Facts(changes=changes, judged=accepted, rejected=memos(failing("M4", 11, "C4")))
    assert weigh(facts, held(checker_add()))[0][2] == "recurred in case M4"  # the 7.2 window of ten cases no longer holds M4; D7 has no window


def test_the_limit_and_the_line_of_one_extension_belong_to_its_item() -> None:
    limits = CharterPair("ceo/AGENT.md", "c1", at(10), keys=(KeyChange("max_children", "2", "3"),), added_after=(LIMITS,), older=at(1))
    changes = ChangeFacts(agents=(agent("ceo/c4-checker", 10, "change cafe00000001", True),), versions=CharterVersions(True, (limits,)))
    rows = weigh(Facts(changes=changes, judged=judged(11)), held(checker_add()))
    assert [(t, k, o) for t, k, o in rows] == [
        ("charter of ceo changed: max_children, added section (2026-11-02), item B1.2", "charter", "INCONCLUSIVE (1 of 3 exercised cases)"),
        ("agent ceo/c4-checker added (2026-11-02), item B1.2", "structural", "INCONCLUSIVE (1 of 3 exercised cases)"),
    ]


def test_a_checker_fix_line_is_weighed_by_the_class_it_names() -> None:
    fix = RecordedItem(1, "checker-fix", "checker-fix|memos|ceo/checker|C4", ("M1",), {"agent": "ceo/checker", "line": LINE})
    line = CharterPair("ceo/checker/AGENT.md", "c2", at(10), added_after=(f"- {LINE} [change cafe00000002]",), older=at(1))
    changes = ChangeFacts(versions=CharterVersions(True, (line,)))
    assert weigh(Facts(changes=changes, judged=judged(11, 12, 13)), held(fix))[0][1:] == ("charter", "not recurred in 3 cases where it was exercised")
    assert weigh(Facts(changes=changes, rejected=memos(failing("M9", 11, "C4"))), held(fix))[0][2] == "recurred in case M9"


def test_a_service_is_weighed_by_its_requests_and_a_later_task_of_the_same_shape() -> None:
    item = RecordedItem(1, "service", "service|ops|T1", ("T1", "T2", "T3"), {"service": "ops/list"})
    service = ServiceFact("ops", "list", at(10), "root", "change cafe00000003")
    shapes = {c: ("everyactionhasanowner",) for c in ("T1", "T2", "T3")}
    effects = EffectFacts(shapes=shapes)
    changes = ChangeFacts(services=(service,))
    base = Facts(changes=changes, effects=effects, judged={"list": (Occasion("L1", "", at(11)),)})
    assert weigh(base, held(item)) == [("service ops/list added (2026-11-02), item B1.1", "structural", "INCONCLUSIVE (1 of 3 exercised cases)")]
    chore = OneOffCase("T9", "ops", "Action list", ("Every action has an owner",), "", at(12), True)
    assert weigh(Facts(changes=changes, effects=effects, one_offs=(chore,)), held(item))[0][2] == "recurred in case T9"
    unjudged = OneOffCase("T9", "ops", "Action list", ("Every action has an owner",), "", at(12), False)
    assert weigh(Facts(changes=changes, effects=effects, one_offs=(unjudged,)), held(item))[0][2] == "INCONCLUSIVE (0 of 3 exercised cases)"
    renamed = ServiceFact("ops", "chores", at(10), "root", "change cafe00000003")
    named = Facts(changes=ChangeFacts(services=(renamed,)), effects=EffectFacts(shapes=shapes, defined=(("ops", "chores", ("everyactionhasanowner",)),)))
    assert weigh(named, held(item))[0][0] == "service ops/chores added (2026-11-02), item B1.1"  # the user renamed it; its criteria are the tasks'


def test_a_change_that_is_the_effect_of_no_item_has_no_target_and_the_first_plan_and_a_taken_back_change_are_not_listed() -> None:
    hand = CharterPair("ceo/writer/AGENT.md", "c3", at(10), body_differs=True, older=at(1))
    changes = ChangeFacts(
        agents=(agent("ceo", 1, "plan abc"), agent("ceo/old", 10, "change cafe00000009 (not applied)"), agent("ceo/hire", 10, "", hired_by="ceo")), versions=CharterVersions(True, (hand,)),
    )
    rows = weigh(Facts(changes=changes), held(checker_add()))
    assert [(t, o) for t, _, o in rows] == [
        ("agent ceo/hire added (2026-11-02)", NOT_EVALUATED), ("charter of ceo/writer changed: body (2026-11-02)", NOT_EVALUATED),
    ]
    assert weigh(Facts(), ()) == []
