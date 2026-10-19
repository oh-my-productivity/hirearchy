"""``LessonsPolicy``: lessons are required on a request for a service and kept short."""

from __future__ import annotations

import pytest

from orgmcp.dispatch import LESSONS_MAX_CHARS
from orgmcp.dispatch._lessons import LessonsPolicy
from orgmcp.dispatch._protocols import LessonsCheck
from orgmcp.kernel import Message, OrgError

from ._support import RED

pytestmark = RED


def task(service: str | None = None) -> Message:
    return Message(sender="root", to="ceo", type="task", body="b", id="20260101T000000000001-root-aaaa", service=service)


@pytest.mark.parametrize("given", [None, "", "  \n "])
def test_an_ordinary_task_needs_no_lessons(given: str | None) -> None:
    assert LessonsPolicy().check(task(), "done", given) == ""


def test_lessons_are_returned_stripped() -> None:
    assert LessonsPolicy().check(task(), "done", "  worked \n") == "worked"


@pytest.mark.parametrize("status", ["done", "failed", "blocked"])
@pytest.mark.parametrize("given", [None, "", " \n"])
def test_a_request_for_a_service_needs_lessons_in_every_final_or_blocked_report(status: str, given: str | None) -> None:
    with pytest.raises(OrgError, match="is a request for service `weekly-brief`: pass `lessons`"):
        LessonsPolicy().check(task("weekly-brief"), status, given)


def test_the_refusal_names_the_task_and_the_service() -> None:
    with pytest.raises(OrgError) as e:
        LessonsPolicy().check(task("weekly-brief"), "blocked", None)
    assert str(e.value).startswith("task 20260101T000000000001-root-aaaa is a request for service `weekly-brief`: pass `lessons` - 1-3 lines")
    assert str(e.value).endswith("say what went wrong and what would have prevented it")


def test_a_status_that_is_not_a_report_status_needs_none() -> None:
    assert LessonsPolicy().check(task("weekly-brief"), "open", None) == ""


def test_the_limit_is_inclusive() -> None:
    assert LessonsPolicy().check(task(), "done", "x" * 800) == "x" * 800
    with pytest.raises(OrgError) as e:
        LessonsPolicy().check(task(), "done", "x" * 801)
    assert str(e.value).startswith("lessons are 801 characters; the limit is 800. Keep 1-3 lines")


def test_the_length_is_that_of_the_stripped_text() -> None:
    assert LessonsPolicy().check(task(), "done", "  " + "x" * 800 + "  \n") == "x" * 800
