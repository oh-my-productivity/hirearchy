"""Contract of ``TaskReporter``: the reporter over the mailboxes on disk, in memory and over numbers for budgets answer alike.

What the callers rely on: a report is a result from the assignee to whoever assigned the task, carrying the body the templates make of the summary and
the lessons; ``done`` and ``failed`` are final, ``blocked`` can be reported again and the new result supersedes it; lessons are required on a request
for a service; the budget the reporter has left travels up with a final result when nothing else needs it; the refusals are the texts agents are shown."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.dispatch import LESSONS_MAX_CHARS, TaskReporter
from orgmcp.dispatch.testing import IMPLEMENTATIONS, DispatchWorld
from orgmcp.kernel import Message, OrgError
from orgmcp.templates.testing import static_document_templates

from ._support import assigned, implementations, make

TEMPLATES = static_document_templates()


@pytest.fixture(params=implementations(IMPLEMENTATIONS[TaskReporter]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DispatchWorld:
    made = make(request, tmp_path)
    assert isinstance(made.reporter, TaskReporter)
    return made


# ------------------------------------------------------------------------------ a report is a result


def test_the_result_goes_to_whoever_assigned_the_task(w: DispatchWorld) -> None:
    task = assigned(w)
    result = w.reporter.report("ceo", task.id, "done", "All criteria met.")
    assert (result.sender, result.to, result.type, result.status) == ("ceo", "root", "result", "done")
    assert (result.reply_to, result.title, result.supersedes) == (task.id, "Work", None)
    assert [m.id for m in w.inbox("root")][-1] == result.id


def test_the_body_is_the_result_text_of_the_templates(w: DispatchWorld) -> None:
    task = assigned(w)
    result = w.reporter.report("ceo", task.id, "done", "All criteria met.")
    assert result.body == TEMPLATES.result_body("All criteria met.", [], "").strip()


def test_the_lessons_are_stripped_and_part_of_the_body(w: DispatchWorld) -> None:
    task = assigned(w)
    result = w.reporter.report("ceo", task.id, "done", "Done.", lessons="  worked well \n")
    assert result.body == TEMPLATES.result_body("Done.", [], "worked well").strip()


def test_the_address_of_the_reporter_may_be_spelled_loosely(w: DispatchWorld) -> None:
    task = assigned(w)
    assert w.reporter.report(" /ceo/ ", task.id, "done", "Done.").sender == "ceo"


def test_an_agent_that_does_not_exist_cannot_report(w: DispatchWorld) -> None:
    with pytest.raises(OrgError, match="no such agent: ghost"):
        w.reporter.report("ghost", "20260101T000000000001-root-aaaa", "done", "Done.")


@pytest.mark.parametrize("status", ["finished", "", "DONE", "open"])
def test_the_status_is_done_failed_or_blocked(w: DispatchWorld, status: str) -> None:
    task = assigned(w)
    with pytest.raises(OrgError) as e:
        w.reporter.report("ceo", task.id, status, "Done.")
    assert str(e.value) == "status must be one of ('done', 'failed', 'blocked')"


# ------------------------------------------------------------------------------ the task must be assigned to the reporter


def test_a_task_that_is_not_there_is_refused_with_the_open_ones(w: DispatchWorld) -> None:
    first, second = assigned(w), assigned(w, runs=3)
    with pytest.raises(OrgError) as e:
        w.reporter.report("ceo", "20260101T000000000001-root-aaaa", "done", "Done.")
    assert str(e.value) == f"no task 20260101T000000000001-root-aaaa assigned to you. Your open tasks: {first.id}, {second.id}"


def test_the_open_tasks_are_none_for_an_agent_without_any(w: DispatchWorld) -> None:
    with pytest.raises(OrgError) as e:
        w.reporter.report("ceo/eng", "20260101T000000000001-root-aaaa", "done", "Done.")
    assert str(e.value) == "no task 20260101T000000000001-root-aaaa assigned to you. Your open tasks: none"


def test_a_task_of_somebody_else_is_not_assigned_to_the_reporter(w: DispatchWorld) -> None:
    task = assigned(w, "ceo/eng")
    with pytest.raises(OrgError, match="no task .* assigned to you. Your open tasks: none"):
        w.reporter.report("ceo/qa", task.id, "done", "Done.")


def test_a_note_is_not_a_task(w: DispatchWorld) -> None:
    note = w.post(Message(sender="root", to="ceo", type="note", body="fyi"))
    with pytest.raises(OrgError, match="no task .* assigned to you"):
        w.reporter.report("ceo", note.id, "done", "Done.")


# ------------------------------------------------------------------------------ final and blocked


FINAL = (
    "task {id} was already reported {status}, and {status} is final (rule 6): it cannot be reported again or changed by a note. Only a task "
    "reported `blocked` can be reported again. If you have information for whoever assigned it, use `send`, as information only: a note does not "
    "change the task's outcome and must not claim that criteria are met."
)


@pytest.mark.parametrize("final", ["done", "failed"])
@pytest.mark.parametrize("again", ["done", "failed", "blocked"])
def test_done_and_failed_are_final(w: DispatchWorld, final: str, again: str) -> None:
    task = assigned(w)
    w.reporter.report("ceo", task.id, final, "First.")
    with pytest.raises(OrgError) as e:
        w.reporter.report("ceo", task.id, again, "Second.")
    assert str(e.value) == FINAL.format(id=task.id, status=final)


def test_a_blocked_task_can_be_reported_again_and_the_new_result_supersedes_it(w: DispatchWorld) -> None:
    task = assigned(w)
    first = w.reporter.report("ceo", task.id, "blocked", "Waiting for data.")
    assert first.supersedes is None
    second = w.reporter.report("ceo", task.id, "done", "Data came.")
    assert second.supersedes == first.id and second.status == "done"


def test_a_task_can_be_reported_blocked_once_per_blocked_report(w: DispatchWorld) -> None:
    task = assigned(w)
    first = w.reporter.report("ceo", task.id, "blocked", "One.")
    second = w.reporter.report("ceo", task.id, "blocked", "Two.")
    third = w.reporter.report("ceo", task.id, "failed", "Three.")
    assert (second.supersedes, third.supersedes) == (first.id, second.id)
    with pytest.raises(OrgError, match="already reported failed"):
        w.reporter.report("ceo", task.id, "done", "Four.")


# ------------------------------------------------------------------------------ lessons


def service_task(w: DispatchWorld) -> Message:
    return assigned(w, service="weekly-brief", contract=1, playbook=0)


@pytest.mark.parametrize("status", ["done", "failed", "blocked"])
def test_lessons_are_required_on_a_request_for_a_service(w: DispatchWorld, status: str) -> None:
    task = service_task(w)
    with pytest.raises(OrgError) as e:
        w.reporter.report("ceo", task.id, status, "Summary.")
    assert str(e.value) == (
        f"task {task.id} is a request for service `weekly-brief`: pass `lessons` - 1-3 lines for the next "
        "request: what worked, what to change in the playbook, and the evidence (runs, rework, review "
        "findings). Required for done, failed and blocked alike: a blocker is the most informative case, so "
        "say what went wrong and what would have prevented it"
    )


def test_lessons_of_only_blanks_are_no_lessons(w: DispatchWorld) -> None:
    task = service_task(w)
    with pytest.raises(OrgError, match="pass `lessons`"):
        w.reporter.report("ceo", task.id, "done", "Summary.", lessons=" \n ")


def test_a_request_for_a_service_is_reported_with_lessons(w: DispatchWorld) -> None:
    task = service_task(w)
    result = w.reporter.report("ceo", task.id, "done", "Summary.", lessons="3 runs, no rework")
    assert result.body == TEMPLATES.result_body("Summary.", [], "3 runs, no rework").strip()


def test_lessons_are_optional_on_an_ordinary_task(w: DispatchWorld) -> None:
    assert w.reporter.report("ceo", assigned(w).id, "done", "Summary.", lessons=None).status == "done"


def test_lessons_may_be_as_long_as_the_limit_and_no_longer(w: DispatchWorld) -> None:
    first, second = assigned(w), assigned(w, runs=3)
    assert w.reporter.report("ceo", first.id, "done", "Summary.", lessons="x" * LESSONS_MAX_CHARS).status == "done"
    with pytest.raises(OrgError) as e:
        w.reporter.report("ceo", second.id, "done", "Summary.", lessons="x" * (LESSONS_MAX_CHARS + 1))
    assert str(e.value) == (
        f"lessons are {LESSONS_MAX_CHARS + 1} characters; the limit is {LESSONS_MAX_CHARS}. Keep 1-3 lines: what worked, "
        "what to change in the playbook, and the evidence; put detail in a file under your work/ directory."
    )


# ------------------------------------------------------------------------------ the budget travels with a final result


def test_a_final_result_carries_back_what_is_left(w: DispatchWorld) -> None:
    task = assigned(w, runs=6)  # ceo made one run
    result = w.reporter.report("ceo", task.id, "done", "Done.")
    assert result.budget == 5 and w.query.budget("ceo") == 0


def test_a_failed_result_carries_it_back_too(w: DispatchWorld) -> None:
    assert w.reporter.report("ceo", assigned(w, runs=4).id, "failed", "Could not.").budget == 3


def test_a_blocked_result_keeps_the_budget_for_the_next_report(w: DispatchWorld) -> None:
    task = assigned(w, runs=6)
    assert w.reporter.report("ceo", task.id, "blocked", "Waiting.").budget == 0
    assert w.query.budget("ceo") == 5
    assert w.reporter.report("ceo", task.id, "done", "Data came.").budget == 5


def test_nothing_is_carried_back_while_other_work_needs_the_runs(w: DispatchWorld) -> None:
    first = assigned(w, runs=6)
    assigned(w, runs=3)  # a second open task
    assert w.reporter.report("ceo", first.id, "done", "Done.").budget == 0


def test_nothing_is_carried_back_to_somebody_who_is_not_the_parent(w: DispatchWorld) -> None:
    task = assigned(w, "ceo/eng", runs=6)  # assigned by root, not by the parent of eng
    assert w.reporter.report("ceo/eng", task.id, "done", "Done.").budget == 0
