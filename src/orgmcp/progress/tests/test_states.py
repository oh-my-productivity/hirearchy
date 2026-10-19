"""``MailTaskStates``: the state of a root task and who is busy."""

from __future__ import annotations

from orgmcp.kernel import ROOT, Message
from orgmcp.progress._ports import TaskState, TaskStates
from orgmcp.progress._states import MailTaskStates
from orgmcp.progress.testing import ProgressWorld

from ._support import XFAIL


def states(w: ProgressWorld) -> MailTaskStates:
    return MailTaskStates(w.mail, w.pauses, w.tasks)


def of(w: ProgressWorld, task: Message, result: Message | None = None, team: tuple[str, ...] = ("ceo", "ceo/eng")) -> TaskState:
    return states(w).state_of(task, result, list(team))


def test_it_is_a_task_state_reader(w: ProgressWorld) -> None:
    assert isinstance(states(w), TaskStates)


@XFAIL
def test_a_final_result_is_its_status(w: ProgressWorld, task: Message) -> None:
    assert of(w, task, w.answer(task, "done", "ok", 0)) == TaskState("done", "")
    assert of(w, task, w.answer(task, "failed", "no", 0)) == TaskState("failed", "")


@XFAIL
def test_a_blocked_result_gives_the_cut_summary_or_says_none_was_given(w: ProgressWorld, task: Message) -> None:
    assert of(w, task, w.answer(task, "blocked", "## Summary\nNeed   the figures.\nSecond line.", 0)).state == "blocked: Need the figures"
    assert of(w, task, w.answer(task, "blocked", "", 0)).state == "blocked: no reason given"
    assert of(w, task, w.answer(task, "blocked", "x" * 300, 0)).state == "blocked: " + "x" * 109 + "…"


@XFAIL
def test_a_team_that_is_gone(w: ProgressWorld, task: Message) -> None:
    assert of(w, task, None, ()) == TaskState("failed: ceo no longer exists", "")


@XFAIL
def test_running_and_unread_work_are_named_and_the_paused_are_not_unread(w: ProgressWorld, task: Message) -> None:
    w.begin_run("ceo")
    w.delegate("ceo", "ceo/eng", "Sub", 2)
    assert of(w, task) == TaskState("working", "running: ceo; unread work: ceo/eng")
    w.pause("ceo/eng", "tired")
    assert of(w, task) == TaskState("working", "running: ceo")


@XFAIL
def test_the_assignee_that_holds_the_task_is_stalled_and_a_pause_is_said(w: ProgressWorld, task: Message) -> None:
    w.begin_run("ceo")
    w.end_run("ceo")
    assert of(w, task) == TaskState("stalled (ceo has not reported and nothing is running)", "")
    w.pause("ceo", "2 failed runs")
    assert of(w, task) == TaskState("stalled (ceo is paused: 2 failed runs)", "")


@XFAIL
def test_the_holders_below_the_assignee_are_named_with_their_pauses(w: ProgressWorld, task: Message) -> None:
    w.begin_run("ceo")
    w.end_run("ceo")
    sub = w.delegate("ceo", "ceo/eng", "Sub", 2)
    w.begin_run("ceo/eng")
    w.end_run("ceo/eng")
    assert of(w, task) == TaskState("waiting on ceo/eng", "")
    w.pause("ceo/eng", "tired")
    assert of(w, task) == TaskState("waiting on ceo/eng (paused: tired)", "")
    assert sub.to == "ceo/eng" and ROOT != sub.to
