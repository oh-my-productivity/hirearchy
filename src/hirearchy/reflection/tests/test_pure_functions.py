"""``version_at``, ``lessons_of``, ``rated``, ``delivered_unrated`` and ``questions_open``: pure functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from hirearchy.kernel import ClientItems, Message, clip_line
from hirearchy.reflection import (
    ITEM_CHARS, ITEMS_SHOWN, Case, Verdict, case_spend, confirmed_criteria, delivered_unrated, items_listing, lessons_of, open_client_items,
    questions_open, rated, user_approved, user_committed, user_cost, user_held, user_spend, version_at,
)
from hirearchy.reflection.api import _user_back
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


def spent(state: str, runs: int, budget: int, returned: int, granted: int = 0) -> int:
    """``case_spend`` of a case with these numbers (nothing else of a case matters to it)."""
    task = Message(sender="root", to="ceo", type="task", body="b", title="t")
    case = Case(
        id="A", service="s", owner="ceo", tasks=[task], result=None, state=state, playbook=0, used=0, reworks=0, budget=budget, runs=runs,
        lessons=[], verdicts=[], started=None, finished=None, returned=returned, user_granted=granted,
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


def test_case_spend_counts_the_user_s_grants_still_held_while_the_case_is_open_or_blocked() -> None:
    """F-G0-2 (m0-s1 6c7a, design 3.2): 15 handed down and 3 granted, 7 used, 8 returned: 7 + (15 + 3 - 7 - 8) = 10; a finished case holds nothing."""
    assert spent("open", 7, 15, 8, granted=3) == 10 and spent("blocked", 7, 15, 8, granted=3) == 10
    assert spent("done", 7, 15, 8, granted=3) == 7 and spent("failed", 7, 15, 8, granted=3) == 7


def test_case_spend_adds_nothing_for_a_grant_that_is_used_up() -> None:
    assert spent("open", 15, 12, 0, granted=3) == 15  # 12 + 3 handed down, all used
    assert spent("blocked", 20, 12, 0, granted=3) == 20  # more used than handed down: never below the runs used
    assert spent("open", 9, 12, 7, granted=3) == 9  # returned beyond what is left: nothing is still out
    assert spent("open", 4, 12, 0, granted=0) == 12  # no grant: today's figure


# ------------------------------------------------------------------------------ user_spend, user_cost, user_committed, user_approved


def hand_built(
    tasks: list[tuple[int, str | None]], state: str = "done", runs: int = 0, returned: int = 0, *, relayed_runs: int = 0, relayed_returned: int = 0,
    relayed_overlap: int = 0, user_granted: int = 0, user_ceiling: int = 0, relayed_to_user: int = 0,
    open_tasks: tuple[str, ...] = (),
) -> Case:
    """A case of a chain of ``(budget, source)`` tasks, with the numbers the pure functions read."""
    chain = [Message(sender="root", to="ceo", type="task", body="b", title="t", budget=b, source=src) for b, src in tasks]
    return Case(
        id="A", service="s", owner="ceo", tasks=chain, result=None, state=state, playbook=0, used=0, reworks=len(chain) - 1,
        budget=sum(b for b, _ in tasks), runs=runs, lessons=[], verdicts=[], started=None, finished=None, returned=returned, relayed_runs=relayed_runs,
        relayed_returned=relayed_returned, relayed_overlap=relayed_overlap, user_granted=user_granted, user_ceiling=user_ceiling,
        relayed_to_user=relayed_to_user, open_tasks=open_tasks,
    )


CHAINS = [[(21, None)], [(10, None), (11, "human")], [(5, None), (8, "human"), (8, None)], [(0, None)]]
NUMBERS = [(12, 0), (15, 0), (14, 0), (16, 0), (7, 8), (9, 15), (20, 0), (0, 0), (2, 0), (7, 21)]


@pytest.mark.parametrize("state", ["done", "failed", "open", "blocked"])
@pytest.mark.parametrize("tasks", CHAINS)
def test_without_a_relayed_task_the_user_spend_and_cost_are_the_case_spend(state: str, tasks: list[tuple[int, str | None]]) -> None:
    """I1 (D-E5-1): a chain without a relayed task costs the user exactly what ``case_spend`` says, so the human client's text is today's text; with
    the user's grants too (0b.1 F-G0-2: both count them while the case is open or blocked)."""
    for runs, returned in NUMBERS:
        for granted in (0, 3):
            case = hand_built(tasks, state, runs, returned, user_granted=granted)
            assert user_spend(case) == user_cost(case) == case_spend(case)


def test_user_spend_leaves_the_runs_of_a_relayed_rework_out() -> None:
    """E5 s1 T6: 15 runs, 5 of them root's relayed rework's, and 1 of the relayed task's 6 returned: the user's requests cost 10."""
    done = hand_built([(12, None), (12, "human"), (6, "relayed")], "done", runs=15, returned=15, relayed_runs=5, relayed_returned=1)
    assert user_spend(done) == 10


def test_user_spend_leaves_the_runs_still_out_of_a_relayed_task_out() -> None:
    """While the case is open, only the user tasks' unused, unreturned budget is still out: the relayed task's 10 are not the user's."""
    case = hand_built([(4, None), (10, "relayed")], "open", runs=2, returned=0)
    assert case_spend(case) == 14 and user_spend(case) == 4  # 2 used + 2 still out of the head's 4; the relayed task's 10 are not the user's


def test_user_spend_of_an_open_case_counts_what_the_user_tasks_returned_only() -> None:
    case = hand_built([(12, None), (6, "relayed")], "open", runs=7, returned=9, relayed_runs=3, relayed_returned=4)
    assert user_spend(case) == 4 + max(0, 12 - 4 - 5)  # 4 user runs; 12 handed down, 5 returned by the user tasks' results


def test_user_spend_counts_the_grants_still_held_beside_a_relayed_task() -> None:
    """F-G0-2: 12 handed down for the user, 2 granted, 6 for a relayed rework; 10 runs, 5 of them the relayed task's: the user's 5 + (12 + 2 - 5), and
    the case's 10 + (18 + 2 - 10)."""
    case = hand_built([(12, None), (6, "relayed")], "open", runs=10, returned=0, relayed_runs=5, user_granted=2)
    assert user_spend(case) == 14 and case_spend(case) == 20
    finished = hand_built([(12, None), (6, "relayed")], "done", runs=10, returned=0, relayed_runs=5, user_granted=2)
    assert user_spend(finished) == 5 and case_spend(finished) == 10


@pytest.mark.parametrize("state", ["open", "blocked"])
@pytest.mark.parametrize("tasks", [*CHAINS, [(12, None), (6, "relayed")], [(10, None), (6, "relayed"), (5, "human")]])
def test_while_open_or_blocked_the_user_spend_is_what_the_user_committed(state: str, tasks: list[tuple[int, str | None]]) -> None:
    """F-G0-2 (design 3.3): the user's spend and the user's committed runs are one figure while the case can still draw on its runs."""
    for runs, returned in NUMBERS:
        for granted in (0, 3):
            for relayed_runs, relayed_to_user in ((0, 0), (min(runs, 2), 1)):
                case = hand_built(
                    tasks, state, runs, returned, user_granted=granted, relayed_runs=relayed_runs,
                    relayed_returned=min(returned, 4) if relayed_runs else 0, relayed_to_user=relayed_to_user if relayed_runs else 0,
                )
                assert user_spend(case) == user_committed(case)


def test_user_cost_subtracts_the_relayed_overlap_and_is_never_below_zero() -> None:
    case = hand_built([(10, None), (6, "relayed"), (5, "human")], "done", runs=9, relayed_runs=2, relayed_overlap=3)
    assert user_spend(case) == 7 and user_cost(case) == 4
    assert user_cost(hand_built([(10, None)], "done", runs=2, relayed_overlap=5)) == 0


def test_user_committed_ignores_the_state_and_counts_the_user_grants() -> None:
    """What a new rework draws on: the user's runs plus what the team still holds for them, whether or not the case is finished."""
    for state in ("done", "failed", "open", "blocked"):
        case = hand_built([(12, None)], state, runs=5, returned=0, user_granted=3)
        assert user_committed(case) == 5 + (12 + 3 - 5)
    assert user_committed(hand_built([(12, None), (6, "relayed")], "done", runs=9, returned=5, relayed_runs=4, relayed_returned=1)) == 5 + (12 - 5 - 4)


def test_user_spend_and_user_committed_read_the_runs_a_relayed_result_carried_back_to_the_user() -> None:
    """D-E6-2, B1 (E6 s3's 9a5b): 5 user runs, 12 handed down, 6 of the relayed result's return are the user's: 5 + (12 - 5 - 6) = 6, in both."""
    for state in ("open", "blocked"):
        case = hand_built([(12, None), (6, "relayed")], state, runs=10, returned=6, relayed_runs=5, relayed_returned=6, relayed_to_user=6)
        before = hand_built([(12, None), (6, "relayed")], state, runs=10, returned=6, relayed_runs=5, relayed_returned=6)
        assert user_spend(case) == user_committed(case) == 5 + (12 - 5 - 6)
        assert user_spend(before) == user_committed(before) == 5 + (12 - 5)  # the 6 read as held, as before B1
    done = hand_built([(12, None), (6, "relayed")], "done", runs=10, returned=6, relayed_runs=5, relayed_returned=6, relayed_to_user=6)
    assert user_spend(done) == 5 and user_committed(done) == 6  # a finished case costs its runs; a new rework still draws on what is held


def test_user_spend_and_user_committed_use_one_helper() -> None:
    """D-E6-2, B1: both read ``_user_back``, so they cannot drift apart (0b reuses ``user_spend`` and ``user_approved``)."""
    case = hand_built([(12, None), (6, "relayed")], "open", runs=10, returned=7, relayed_runs=5, relayed_returned=6, relayed_to_user=2)
    assert _user_back(case) == 7 - 6 + 2
    assert user_spend(case) == user_committed(case) == 5 + max(0, 12 - 5 - _user_back(case))


def test_user_committed_is_never_below_the_users_charged_runs() -> None:
    """D-E6-2, B1: whatever the relayed results carried back, the user is credited no more than the team held: ``left`` never exceeds what the user
    approved and has not used."""
    for to_user in (0, 1, 6, 50, 10_000):
        for state in ("done", "open", "blocked"):
            case = hand_built([(12, None), (6, "relayed")], state, runs=10, returned=6, relayed_runs=5, relayed_returned=6, relayed_to_user=to_user)
            assert user_committed(case) >= case.runs - case.relayed_runs and user_spend(case) >= case.runs - case.relayed_runs


def rework_of(task_id: str, budget: int) -> Message:
    return Message(sender="root", to="ceo", type="task", body="b", title="t", budget=budget, revises=task_id, source="human")


def test_user_held_is_what_the_team_still_holds_of_the_users_runs_for_an_open_revised_task() -> None:
    """D-E6-2, B2 (design 5.3): committed 10 (2 used, 8 held, the rework's 1 among them), less the 2 used and the rework's own 1: 7 are held."""
    case = hand_built([(9, None), (1, "human")], "open", runs=2, open_tasks=("T1",))
    assert user_committed(case) == 2 + (10 - 2) and user_held(case, rework_of("T1", 1)) == 7


def test_user_held_leaves_the_relayed_runs_and_what_came_back_to_the_user_out() -> None:
    """E6 s3's bc02 shape: 17 committed, 5 charged, the rework's 1: 11 are held. The relayed runs are not the user's, and what a relayed
    result carried back to the user is no longer held."""
    case = hand_built([(16, None), (1, "human")], "open", runs=5, open_tasks=("T1",))
    assert user_held(case, rework_of("T1", 1)) == 11
    relayed = hand_built(
        [(12, None), (6, "relayed"), (1, "human")], "open", runs=9, returned=6, relayed_runs=4, relayed_returned=6, relayed_to_user=6,
        open_tasks=("T1",),
    )
    assert user_committed(relayed) == 5 + (13 - 5 - 6) and user_held(relayed, rework_of("T1", 1)) == 1  # 7 committed, 5 used by the user, 1 the rework's


def test_user_held_is_zero_when_the_revised_task_is_closed_or_not_in_the_case() -> None:
    case = hand_built([(10, None)], "done", runs=2, open_tasks=("T1",))
    assert user_held(case, rework_of("T2", 1)) == 0  # not an open task of the case
    assert user_held(case, rework_of("", 1)) == 0
    assert user_held(hand_built([(10, None)], "done", runs=2), rework_of("T1", 1)) == 0  # a hand-built Case has no open task


def test_user_held_is_never_below_zero() -> None:
    case = hand_built([(3, None)], "open", runs=9, open_tasks=("T1",))  # more used than handed down
    assert user_held(case, rework_of("T1", 5)) == 0
    assert user_held(hand_built([(3, None)], "open", runs=3, open_tasks=("T1",)), rework_of("T1", 1)) == 0  # all used


def test_user_approved_is_the_contract_budget_for_a_hand_built_case_and_the_ceiling_when_that_is_higher() -> None:
    case = hand_built([(12, None)])
    assert user_approved(case, 12) == 12 and user_approved(case, 7) == 7
    assert user_approved(hand_built([(12, None)], user_ceiling=17), 12) == 17
    assert user_approved(hand_built([(12, None)], user_ceiling=5), 12) == 12


def test_a_hand_built_case_has_no_unapproved_rework_and_the_approval_reads_as_before() -> None:
    """D-E7-2 A2: ``Case.unapproved_reworks`` defaults to ``()``, so every hand-built case keeps today's approval."""
    case = hand_built([(12, None), (1, "human")], user_ceiling=12)
    assert case.unapproved_reworks == () and user_approved(case, 12) == 12


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


def test_rated_human_counts_only_the_users_own_verdict() -> None:
    """D-E7-2 C: ``rated(case, task, human=True)`` is ``rated`` with only human-tier verdicts; the default stays any tier."""
    first, second = chain("1", "2")
    for tier, counts in (("human", True), ("relayed", False), ("agent", False)):
        found = case_with([first, second], verdict_at(0, [first, second], tier=tier, kind="accept"))
        assert rated(found, first, human=True) is counts, tier
        assert rated(found, first) is True, tier  # any tier, as before


def test_rated_human_follows_the_step_of_the_task() -> None:
    """D-E7-2 C: a human verdict at the task's step or after it rates the task; one before it does not; a relayed one after it does not either."""
    first, second, third = chain("1", "2", "3")
    tasks = [first, second, third]
    at = case_with(tasks, verdict_at(1, tasks))
    assert rated(at, second, human=True) is True  # at the task's step
    assert rated(at, first, human=True) is True  # after the task's step (a later rework's verdict)
    assert rated(at, third, human=True) is False  # before the task's step
    relayed_after = case_with(tasks, verdict_at(0, tasks, tier="human"), verdict_at(2, tasks, tier="relayed", n=2))
    assert rated(relayed_after, second, human=True) is False  # the human verdict is before step 1 and the relayed one does not count
    assert rated(relayed_after, second) is True
    assert rated(None, first, human=True) is False and rated(case_with(tasks), first, human=True) is False


# ------------------------------------------------------------------------------ questions_open

# D-E6-1 (A2): ``questions_open`` counts only the items that name a criterion id (``C<k>``); these two do, so the tests below keep testing the question path.
ASKED = "## Summary\nok\n\nQuestions for the client:\n- C1: Keep Marta's row?\n- C2: Which Friday?\n\n## Artifacts\n- a/b.md"


def answered(task: Message, status: str, body: str) -> Message:
    return Message(sender="ceo", to="root", type="result", reply_to=task.id, status=status, body=body)


def root_rework(task: Message, source: str | None) -> Message:
    return Message(sender="root", to="ceo", type="task", title="again", body="goal", revises=task.id, source=source)


def test_questions_open_counts_done_and_blocked_results() -> None:
    (task,) = chain("1")
    found = case_with([task])
    assert questions_open(task, answered(task, "done", ASKED), found, []) == 2
    assert questions_open(task, answered(task, "blocked", ASKED), found, []) == 2  # a blocked result asks too (6.1)
    assert questions_open(task, answered(task, "failed", ASKED), found, []) == 0  # a failed one has nothing to copy or deliver
    one = answered(task, "done", "Questions for the client: C2: Which Friday?\n\n## Artifacts\n- a.md")  # D-E6-1: the item names C2
    assert questions_open(task, one, found, []) == 1


def test_questions_open_is_0_once_rated_or_reworked_by_a_human() -> None:
    first, second = chain("1", "2")
    result = answered(first, "done", ASKED)
    assert questions_open(first, result, case_with([first, second], verdict_at(0, [first, second], kind="accept")), []) == 0  # the client's verdict
    assert questions_open(first, result, case_with([first, second]), [root_rework(first, "human")]) == 0  # the user asked for the rework
    assert questions_open(first, result, case_with([first, second]), [root_rework(second, "human")]) == 2  # a rework of another task settles nothing
    assert questions_open(first, result, case_with([first, second], verdict_at(1, [first, second], kind="accept")), []) == 0  # a later rework's verdict


def test_a_relayed_rework_does_not_settle_questions() -> None:
    (task,) = chain("1")
    result = answered(task, "blocked", ASKED)
    for source in (None, "relayed"):
        assert questions_open(task, result, case_with([task]), [root_rework(task, source)]) == 2  # 0a.1 DR-17
    not_a_rework = Message(sender="root", to="ceo", type="note", body="b", revises=task.id, source="human")
    assert questions_open(task, result, case_with([task]), [not_a_rework]) == 2


def test_a_relayed_or_agent_verdict_settles_no_question_and_a_human_one_does() -> None:
    """D-E7-2 C: only the user's own verdict (human tier) on the delivery or on a later rework of it settles the questions and the notes."""
    first, second = chain("1", "2")
    tasks = [first, second]
    result = answered(first, "done", MIXED)
    for tier in ("relayed", "agent"):
        for kind in ("accept", "reject"):
            for step in (0, 1):  # at the task's step and at a later one
                case = case_with(tasks, verdict_at(step, tasks, tier=tier, kind=kind))
                assert questions_open(first, result, case, []) == 2, (tier, kind, step)
                assert open_client_items(first, result, case, []) == BOTH, (tier, kind, step)
    for kind in ("accept", "reject"):
        for step in (0, 1):
            case = case_with(tasks, verdict_at(step, tasks, kind=kind))
            assert questions_open(first, result, case, []) == 0, (kind, step)
            assert open_client_items(first, result, case, []) == ClientItems(), (kind, step)
    relayed_then_human = case_with(tasks, verdict_at(0, tasks, tier="relayed", n=1), verdict_at(1, tasks, tier="human", kind="accept", n=2))
    assert questions_open(first, result, relayed_then_human, []) == 0  # a human verdict on the later rework settles it


def test_no_questions_gives_0() -> None:
    (task,) = chain("1")
    for body in ("ok, nothing asked", "Questions for the client: none.\n\n## Artifacts\n- a.md", "Questions for the client:\n\n## Lessons\n- x", ""):
        assert questions_open(task, answered(task, "done", body), case_with([task]), []) == 0
    assert questions_open(task, answered(task, "done", ASKED), None, []) == 2  # a one-off task has no case: only a human rework settles it
    one_off = Message(id="9", sender="root", to="ceo", type="task", body="b", title="one off")  # no service: a verdict cannot settle it
    assert questions_open(one_off, answered(one_off, "done", ASKED), case_with(chain("9"), verdict_at(0, chain("9"), kind="accept")), []) == 2


# ------------------------------------------------------------------------------ open_client_items, items_listing (D-E6-1, A2)

MIXED = "## Summary\nok\n\nQuestions for the client:\n- C1: Keep Marta's row?\n- Style: 'himself' in Sam's row (reviewer: harmless).\n- C2: Which Friday?\n\n## Artifacts\n- a/b.md"
BOTH = ClientItems(("C1: Keep Marta's row?", "C2: Which Friday?"), ("Style: 'himself' in Sam's row (reviewer: harmless).",))


def test_open_client_items_splits_the_block_into_questions_and_notes() -> None:
    (task,) = chain("1")
    found = case_with([task])
    assert open_client_items(task, answered(task, "done", MIXED), found, []) == BOTH
    assert open_client_items(task, answered(task, "blocked", MIXED), found, []) == BOTH  # a blocked result asks too
    assert open_client_items(task, answered(task, "failed", MIXED), found, []) == ClientItems()  # a failed one has nothing to copy or deliver
    assert open_client_items(task, answered(task, "done", "ok, nothing asked"), found, []) == ClientItems()
    assert open_client_items(task, answered(task, "done", "Questions for the client: none."), found, []) == ClientItems()


def test_open_client_items_settles_questions_and_notes_together() -> None:
    first, second = chain("1", "2")
    result = answered(first, "done", MIXED)
    rated_case = case_with([first, second], verdict_at(0, [first, second], kind="accept"))
    assert open_client_items(first, result, rated_case, []) == ClientItems()  # the client's verdict
    assert open_client_items(first, result, case_with([first, second]), [root_rework(first, "human")]) == ClientItems()  # the user asked for the rework
    assert open_client_items(first, result, case_with([first, second]), [root_rework(second, "human")]) == BOTH  # a rework of another task settles nothing
    later = case_with([first, second], verdict_at(1, [first, second], kind="accept"))
    assert open_client_items(first, result, later, []) == ClientItems()  # a later rework's verdict


def test_open_client_items_keeps_both_parts_under_a_relayed_rework() -> None:
    (task,) = chain("1")
    for source in (None, "relayed"):
        assert open_client_items(task, answered(task, "done", MIXED), case_with([task]), [root_rework(task, source)]) == BOTH  # 0a.1 DR-17
    assert open_client_items(task, answered(task, "done", MIXED), None, []) == BOTH  # a one-off task has no case


def test_questions_open_counts_only_the_items_that_name_a_criterion_id() -> None:
    (task,) = chain("1")
    found = case_with([task])
    assert questions_open(task, answered(task, "done", MIXED), found, []) == 2
    notes_only = "Questions for the client:\n- Style: 'himself' (reviewer: harmless).\n- Typo in row 2."
    assert questions_open(task, answered(task, "done", notes_only), found, []) == 0
    assert questions_open(task, answered(task, "blocked", notes_only), found, []) == 0
    assert questions_open(task, answered(task, "done", "Questions for the client: C4: exclude non-actions?\n- a note"), found, []) == 1


def test_items_listing_shows_five_and_counts_the_rest() -> None:
    assert (ITEM_CHARS, ITEMS_SHOWN) == (160, 5)
    assert items_listing([]) == ""
    assert items_listing(["a?"]) == "a?"
    assert items_listing([f"q{i}?" for i in range(1, 6)]) == "q1?; q2?; q3?; q4?; q5?"  # five: no suffix
    assert items_listing([f"q{i}?" for i in range(1, 7)]) == "q1?; q2?; q3?; q4?; q5?; and 1 more"
    assert items_listing([f"q{i}?" for i in range(1, 9)]) == "q1?; q2?; q3?; q4?; q5?; and 3 more"


def test_items_listing_clips_each_item_to_160_characters() -> None:
    long = "Is this the long item? " * 12
    out = items_listing([long, "second?"])
    assert out == f"{clip_line(long, 160)}; second?" and len(clip_line(long, 160)) == 160 and long.strip() not in out
