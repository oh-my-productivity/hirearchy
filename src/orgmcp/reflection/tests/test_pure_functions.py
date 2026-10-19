"""``version_at`` and ``lessons_of``: pure functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from orgmcp.kernel import Message
from orgmcp.reflection import lessons_of, version_at

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
