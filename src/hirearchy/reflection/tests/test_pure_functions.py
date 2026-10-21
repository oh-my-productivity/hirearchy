"""``version_at`` and ``lessons_of``: pure functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from hirearchy.kernel import Message
from hirearchy.reflection import Case, case_spend, lessons_of, version_at

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
