"""``version_at`` and ``lessons_of``: pure functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from hirearchy.kernel import Message
from hirearchy.reflection import Case, Verdict, case_spend, confirmed_criteria, delivered_unrated, lessons_of, rated, version_at
from hirearchy.services import Criterion

T = datetime(2026, 1, 1, tzinfo=timezone.utc)
TIMELINE = [(1, T), (2, T + timedelta(days=1)), (3, T + timedelta(days=2))]


def result(body: str) -> Message:
    return Message(sender="ceo", to="root", type="result", body=body)


# ------------------------------------------------------------------------------ version_at


def test_now_is_the_latest_version() -> None:
    assert version_at(TIMELINE, None) == 3


def test_a_version_is_in_force_from_the_moment_it_was_written() -> None:
    assert version_at(TIMELINE, T) == 1 and version_at(TIMELINE, T + timedelta(days=1)) == 2


def test_between_two_versions_the_earlier_one_is_in_force() -> None:
    assert version_at(TIMELINE, T + timedelta(hours=36)) == 2


def test_before_the_first_version_there_is_none() -> None:
    assert version_at(TIMELINE, T - timedelta(seconds=1)) == 0 and version_at([], None) == 0


def test_the_timeline_need_not_be_sorted() -> None:
    assert version_at(list(reversed(TIMELINE)), T + timedelta(hours=1)) == 1


# ------------------------------------------------------------------------------ lessons_of


def test_a_result_without_a_lessons_section_has_none() -> None:
    assert lessons_of(result("Delivered.")) == ""


def test_the_section_runs_to_the_next_heading() -> None:
    assert lessons_of(result("Done.\n\n## Lessons\nSearch first.\nTwo runs.\n\n## Notes\nignored")) == "Search first.\nTwo runs."


def test_the_heading_is_matched_without_regard_to_case_or_spaces() -> None:
    assert lessons_of(result("## LESSONS  \nx")) == "x"


def test_the_last_section_runs_to_the_end_and_is_trimmed() -> None:
    assert lessons_of(result("## Lessons\n\n  one  \n\n")) == "one"


def test_another_heading_is_not_the_section() -> None:
    assert lessons_of(result("## Notes\nnot a lesson\n### Lessons\nnope")) == ""


def test_a_second_lessons_section_adds_to_the_first() -> None:
    assert lessons_of(result("## Lessons\na\n## Other\nb\n## Lessons\nc")) == "a\nc"


# ------------------------------------------------------------------------------ case_spend


def spent(state: str, runs: int, budget: int, returned: int) -> int:
    """``case_spend`` of a case with these numbers (nothing else of a case matters to it)."""
    task = Message(sender="root", to="ceo", type="task", body="b", title="t")
    case = Case(
        id="A", service="s", owner="ceo", tasks=[task], result=None, state=state, playbook=0, used=0, reworks=0, budget=budget, runs=runs,
        lessons=[], verdicts=[], started=None, finished=None, returned=returned,
    )
    return case_spend(case)


def test_case_spend_on_e3s_cases() -> None:
    contract = 15  # the per-request budget of study E3
    for runs, handed in ((12, 21), (15, 25), (14, 20)):
        assert spent("done", runs, handed, 0) == runs and spent("done", runs, handed, 0) <= contract
    assert spent("done", 16, 15, 0) == 16 > contract


def test_case_spend_counts_runs_still_out_while_open() -> None:
    assert spent("open", 7, 21, 8) == 13 and spent("blocked", 7, 21, 8) == 13
    assert spent("done", 7, 21, 8) == 7 and spent("failed", 7, 21, 8) == 7


def test_case_spend_never_counts_a_negative_rest() -> None:
    assert spent("open", 9, 21, 15) == 9  # returned > budget - runs: nothing is still out
    assert spent("open", 20, 15, 0) == 20  # more used than handed down


def test_case_spend_of_a_case_with_nothing_handed_down_is_its_runs() -> None:
    assert spent("open", 0, 0, 0) == 0 and spent("open", 2, 0, 0) == 2


# ------------------------------------------------------------------------------ confirmed_criteria


def judged(*, links: tuple[str, ...] = (), links_tier: str = "", confirmed: tuple[str, ...] = (), n: int = 1) -> Verdict:
    note = Message(id=f"2026010100000{n}000000-root-000{n}", sender="root", to="ceo", type="note", body="No.", feedback="reject")
    return Verdict("reject", "No.", None, "T", 0, note, links=links, links_tier=links_tier, confirmed=confirmed)


def with_verdicts(*verdicts: Verdict) -> Case:
    task = Message(sender="root", to="ceo", type="task", body="b", title="t")
    return Case(
        id="A", service="s", owner="ceo", tasks=[task], result=None, state="done", playbook=0, used=0, reworks=0, budget=1, runs=1, lessons=[],
        verdicts=list(verdicts), started=None, finished=None,
    )


def test_confirmed_criteria_reads_human_links_only() -> None:
    relayed_link = judged(links=("C1",), links_tier="relayed")  # the assistant's own reading
    own_criterion = judged(links=("C2",), links_tier="relayed", n=2)  # a criterion on the rejection itself
    nothing = judged(links=("none",), links_tier="human", n=3)  # "none" and R<j> name no criterion
    same_as = judged(links=("R1",), links_tier="human", n=4)
    assert confirmed_criteria([with_verdicts(relayed_link, own_criterion, nothing, same_as)], []) == frozenset()
    yes = judged(links=("C3",), links_tier="human", confirmed=("C3",), n=5)
    more = judged(links=("C4", "R1"), links_tier="human", confirmed=("C4",), n=6)
    assert confirmed_criteria([with_verdicts(yes), with_verdicts(more, relayed_link)], []) == frozenset({"C3", "C4"})  # united over cases
    assert confirmed_criteria([], []) == frozenset() and confirmed_criteria([with_verdicts()], []) == frozenset()


def criterion(id: str, *, since: int = 2, by: str = "root", answers: str = "", user: bool = False) -> Criterion:
    return Criterion(id, f"text of {id}", since, by, True, answers, user)


def test_an_answered_criterion_is_confirmed_only_by_a_human_link_on_its_rejection() -> None:
    mine = judged(links=("C3",), links_tier="human", confirmed=("C3",), n=5)  # the rejection the amendment answers
    other = judged(links=("C3",), links_tier="human", confirmed=("C3",), n=6)  # a later, unrelated link that names C3
    answered = criterion("C3", answers=mine.message.id)
    assert confirmed_criteria([with_verdicts(other)], [answered]) == frozenset()  # a link on another rejection confirms nothing
    assert confirmed_criteria([with_verdicts(mine)], [answered]) == frozenset({"C3"})  # the product's own link, on that rejection
    assert confirmed_criteria([with_verdicts(other), with_verdicts(mine)], [answered]) == frozenset({"C3"})
    unlinked = judged(n=7)  # the rejection is there, its link is not (the write failed): nothing is confirmed
    assert confirmed_criteria([with_verdicts(unlinked)], [criterion("C3", answers=unlinked.message.id)]) == frozenset()


def test_a_user_initiated_criterion_is_never_confirmed() -> None:
    yes = judged(links=("C3", "C4"), links_tier="human", confirmed=("C3", "C4"))
    assert confirmed_criteria([with_verdicts(yes)], [criterion("C3", user=True), criterion("C4")]) == frozenset({"C4"})
    assert confirmed_criteria([with_verdicts(yes)], [criterion("C3", user=True), criterion("C4", user=True)]) == frozenset()


def test_a_legacy_or_v1_criterion_is_confirmed_as_in_0a1() -> None:
    yes = judged(links=("C1", "C3", "C5"), links_tier="human", confirmed=("C1", "C3", "C5"))
    both = [criterion("C1", since=1), criterion("C3")]  # a v1 criterion; an amendment written before 0a.2 (no basis)
    assert confirmed_criteria([with_verdicts(yes)], both) == frozenset({"C1", "C3", "C5"})  # C5: an id the criteria do not list
    assert confirmed_criteria([with_verdicts(yes)], []) == frozenset({"C1", "C3", "C5"})


# ------------------------------------------------------------------------------ rated and delivered_unrated


def chain(*ids: str) -> list[Message]:
    return [Message(id=i, sender="root", to="ceo", type="task", body="b", title=f"task {i}", service="s") for i in ids]


def verdict_at(step: int, tasks: list[Message], *, tier: str = "human", kind: str = "reject", n: int = 1) -> Verdict:
    note = Message(id=f"2026010100000{n}000000-root-000{n}", sender="root", to="ceo", type="note", body="b", feedback=kind)
    return Verdict(kind, "b", None, tasks[step].id, step, note, tier=tier)


def case_with(tasks: list[Message], *verdicts: Verdict, state: str = "done", id: str | None = None) -> Case:
    return Case(
        id=id or tasks[0].id, service="s", owner="ceo", tasks=tasks, result=None, state=state, playbook=0, used=0, reworks=len(tasks) - 1, budget=1,
        runs=1, lessons=[], verdicts=list(verdicts), started=None, finished=None,
    )


def test_rated_is_unchanged_after_the_move() -> None:
    """The rule ``progress`` had (a verdict on a delivery or on a later rework of it), now in ``reflection``."""
    first, second = chain("1", "2")
    found = case_with([first, second], verdict_at(0, [first, second]))
    assert rated(found, first) is True and rated(found, second) is False  # a verdict on the first delivery does not rate its rework
    later = case_with([first, second], verdict_at(1, [first, second]))
    assert rated(later, first) is True and rated(later, second) is True  # a verdict on the rework rates the delivery it replaced
    assert rated(case_with([first, second]), first) is False and rated(None, first) is False


def test_delivered_unrated_names_the_latest_task_of_each_done_unrated_case() -> None:
    a, b, c = chain("a1", "a2"), chain("b1"), chain("c1")
    cases = [
        case_with(a, verdict_at(0, a, n=1)),  # reworked after its verdict: the rework a2 is delivered and unrated
        case_with(b, id="b1"),  # delivered, no verdict
        case_with(c, verdict_at(0, c, kind="accept", n=2)),  # rated
    ]
    assert delivered_unrated(cases) == ("a2", "b1")


def test_a_blocked_or_failed_case_is_not_unrated() -> None:
    one, two, three = chain("o1"), chain("t1"), chain("h1")
    assert delivered_unrated([case_with(one, state="blocked"), case_with(two, state="failed"), case_with(three, state="open")]) == ()


def test_a_relayed_verdict_counts_as_rated() -> None:
    one, two = chain("r1"), chain("a1")
    cases = [case_with(one, verdict_at(0, one, tier="relayed", kind="accept")), case_with(two, verdict_at(0, two, tier="agent", n=2))]
    assert delivered_unrated(cases) == ()  # any tier is a verdict: root can always meet the condition (a relayed accept)


def test_a_later_rework_carries_the_rating() -> None:
    tasks = chain("1", "2", "3")
    assert delivered_unrated([case_with(tasks, verdict_at(2, tasks))]) == ()  # the verdict on the last rework rates the whole chain
    assert delivered_unrated([case_with(tasks, verdict_at(1, tasks))]) == ("3",)  # a verdict on the second does not rate the third


def test_no_cases_gives_no_unrated() -> None:
    assert delivered_unrated([]) == ()
