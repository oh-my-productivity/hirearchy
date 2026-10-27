"""``LessonsPolicy``: lessons are required on a request for a service and kept short."""

from __future__ import annotations

import pytest

from hirearchy.dispatch import LESSONS_MAX_CHARS, check_lessons
from hirearchy.dispatch._lessons import LessonsPolicy
from hirearchy.kernel import Message, OrgError



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
    assert str(e.value).startswith("task 20260101T000000000001-root-aaaa is a request for service `weekly-brief`: pass `lessons` - an after-action review")
    assert str(e.value).endswith("say what went wrong and what would have prevented it")


def test_a_status_that_is_not_a_report_status_needs_none() -> None:
    assert LessonsPolicy().check(task("weekly-brief"), "open", None) == ""


def test_the_limit_is_inclusive() -> None:
    assert LessonsPolicy().check(task(), "done", "x" * 800) == "x" * 800
    with pytest.raises(OrgError) as e:
        LessonsPolicy().check(task(), "done", "x" * 801)
    assert str(e.value).startswith("lessons are 801 characters; the limit is 800. Keep the after-action review short")


def test_the_length_is_that_of_the_stripped_text() -> None:
    assert LessonsPolicy().check(task(), "done", "  " + "x" * 800 + "  \n") == "x" * 800


@pytest.mark.parametrize(
    ("service", "status", "given"),
    [(None, "done", None), (None, "done", "  worked \n"), ("weekly-brief", "done", "ok"), ("weekly-brief", "blocked", ""), ("weekly-brief", "failed", "x" * (LESSONS_MAX_CHARS + 1))],
)
def test_the_function_is_the_rule_of_the_policy(service: str | None, status: str, given: str | None) -> None:
    """``check_lessons`` is what ``Org._check_lessons`` (static) calls; the policy and the function answer, or refuse, alike."""
    outcomes = []
    for check in (check_lessons, LessonsPolicy().check):
        try:
            outcomes.append(("returned", check(task(service), status, given)))
        except OrgError as error:
            outcomes.append(("refused", str(error)))
    assert outcomes[0] == outcomes[1]


AAR_FORM = (
    "Expected: <the criterion id or step it concerns>. Happened: <what the work did>. Caught at: <where it should have been caught>. Cause: <the "
    "system cause: a step, a check, a hand-off, an input; not a person>. Prevent: <what would have prevented it>. When nothing went wrong: Near "
    "miss: <what almost went wrong, or none>."
)


def test_the_refusal_asks_for_the_after_action_review_form() -> None:
    with pytest.raises(OrgError) as e:
        LessonsPolicy().check(task("weekly-brief"), "done", None)
    assert str(e.value) == (
        "task 20260101T000000000001-root-aaaa is a request for service `weekly-brief`: pass `lessons` - an after-action review of the work, in "
        f"these labelled parts: {AAR_FORM} Required for done, failed and blocked alike: a blocker is the most informative case, so say what went "
        "wrong and what would have prevented it"
    )
    assert "1-3 lines" not in str(e.value)


def test_the_too_long_refusal_asks_for_a_shorter_review() -> None:
    with pytest.raises(OrgError) as e:
        LessonsPolicy().check(task("weekly-brief"), "done", "x" * 801)
    assert str(e.value) == (
        f"lessons are 801 characters; the limit is 800. Keep the after-action review short: {AAR_FORM} Put detail in a file under your work/ directory."
    )
