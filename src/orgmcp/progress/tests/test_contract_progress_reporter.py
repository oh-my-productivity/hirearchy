"""Every ``ProgressReporter`` - over files and over memory - says the same of an organization: the lines, the waits and the scheduler line."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.attention import Waiting
from orgmcp.daemon import SchedulerState
from orgmcp.kernel import ROOT, Message, OrgError
from orgmcp.progress import WAIT_MAX, ProgressReporter
from orgmcp.progress.testing import IMPLEMENTATIONS, ProgressWorld

from ._support import XFAIL


@pytest.fixture(params=IMPLEMENTATIONS[ProgressReporter], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ProgressWorld:
    """``ceo`` and ``ceo/eng`` exist; nothing else does."""
    made = cast(Callable[[Path], ProgressWorld], request.param)(tmp_path)
    assert isinstance(made.reporter, ProgressReporter)
    made.hire("ceo")
    made.hire("ceo/eng")
    return made


def lines(w: ProgressWorld, task_id: str | None = None) -> list[str]:
    return w.reporter.progress(task_id).splitlines()


def read(w: ProgressWorld, addr: str) -> None:
    w.begin_run(addr)
    w.end_run(addr)


# ------------------------------------------------------------------------------------------------ the lines


@XFAIL
def test_no_tasks(w: ProgressWorld) -> None:
    assert w.reporter.progress() == "No open tasks."


@XFAIL
def test_a_task_nobody_has_started_is_working_with_unread_work(w: ProgressWorld, task: Message) -> None:
    (line,) = lines(w)
    assert line.startswith('"Write the report": working. unread work: ceo. runs 0 of 8.') and line.endswith(f"(task {task.id})")


@XFAIL
def test_a_running_agent_is_named_with_the_runs_used_so_far(w: ProgressWorld, task: Message) -> None:
    w.begin_run("ceo")
    w.use_run("ceo")
    (line,) = lines(w)
    assert '"Write the report": working. running: ceo. runs 1 of 8.' in line


@XFAIL
def test_working_covers_the_whole_subtree(w: ProgressWorld, task: Message) -> None:
    read(w, "ceo")
    w.delegate("ceo", "ceo/eng", "Sub", 3)
    assert "working. unread work: ceo/eng." in lines(w)[0]


@XFAIL
def test_waiting_on_the_agent_that_holds_the_work(w: ProgressWorld, task: Message) -> None:
    read(w, "ceo")
    w.delegate("ceo", "ceo/eng", "Sub", 3)
    read(w, "ceo/eng")
    assert '"Write the report": waiting on ceo/eng.' in lines(w)[0]


@XFAIL
def test_a_paused_holder_says_why(w: ProgressWorld, task: Message) -> None:
    read(w, "ceo")
    w.delegate("ceo", "ceo/eng", "Sub", 3)
    read(w, "ceo/eng")
    w.pause("ceo/eng", "2 failed runs")
    assert "waiting on ceo/eng (paused: 2 failed runs)." in lines(w)[0]


@XFAIL
def test_stalled_when_the_assignee_itself_holds_the_task(w: ProgressWorld, task: Message) -> None:
    read(w, "ceo")
    assert '"Write the report": stalled (ceo has not reported and nothing is running).' in lines(w)[0]
    w.pause("ceo", "tired")
    assert "stalled (ceo is paused: tired)." in lines(w)[0]


@XFAIL
def test_blocked_with_the_first_line_of_the_summary(w: ProgressWorld, task: Message) -> None:
    read(w, "ceo")
    w.answer(task, "blocked", "## Summary\nNeed the 2025 sales figures.\n\n## Questions\nWhich year?", 0)
    assert '"Write the report": blocked: Need the 2025 sales figures.' in lines(w)[0]


@XFAIL
def test_done_shows_the_artifacts_and_the_returned_runs(w: ProgressWorld, task: Message) -> None:
    w.begin_run("ceo")
    w.use_run("ceo")
    w.answer(task, "done", "## Summary\nAll good.\n\n## Artifacts\n- ceo/work/report.md (3 words)\n- ceo/work/notes.md", 7)
    (line,) = lines(w)
    assert '"Write the report": done.' in line and "runs 1 of 8 (7 returned)." in line
    assert "artifacts: ceo/work/report.md, ceo/work/notes.md." in line and "words" not in line


@XFAIL
def test_failed_and_a_done_without_artifacts(w: ProgressWorld, task: Message) -> None:
    w.answer(task, "failed", "The source site is gone.", 0)
    assert '"Write the report": failed.' in lines(w)[0] and "no artifacts" in lines(w)[0]


@XFAIL
def test_an_assignee_that_no_longer_exists(w: ProgressWorld, task: Message) -> None:
    w.retire("ceo")
    assert '"Write the report": failed: ceo no longer exists. runs 0 of 8.' in lines(w)[0]


@XFAIL
def test_the_runs_of_the_whole_subtree_count_and_later_grants_add_to_the_budget(w: ProgressWorld, task: Message) -> None:
    w.use_run("ceo")
    w.use_run("ceo/eng")
    w.use_run("ceo/eng")
    w.write(ROOT, "ceo", "More runs", "Here are 3 more.", 3)
    assert "runs 3 of 11." in lines(w)[0]


@XFAIL
def test_what_needs_the_user_follows_the_tasks(w: ProgressWorld, task: Message) -> None:
    w.queue.entries = [("m1", 'Needs you: note from ceo "Budget request": 2 more (message m1)'), ("m2", "Needs you: second (message m2)")]
    assert lines(w)[1:] == ['Needs you: note from ceo "Budget request": 2 more (message m1)', "Needs you: second (message m2)"]


@XFAIL
def test_one_task_by_id_in_any_state_and_unknown_ids_are_refused(w: ProgressWorld, task: Message) -> None:
    other = w.delegate(ROOT, "ceo/eng", "Other", 2)
    assert len(lines(w)) == 2
    assert lines(w, other.id)[0].startswith('"Other": working.')
    with pytest.raises(OrgError, match=f"no task nope given by root. Tasks: {task.id}, {other.id}"):
        w.reporter.progress("nope")


@XFAIL
def test_no_task_at_all_and_an_unknown_id(w: ProgressWorld) -> None:
    with pytest.raises(OrgError, match="no task nope given by root. Tasks: none"):
        w.reporter.progress("nope")


@XFAIL
def test_finished_tasks_are_listed_for_a_day_then_only_as_the_last_one(w: ProgressWorld, task: Message) -> None:
    w.answer(task, "done", "ok", 0)
    assert lines(w)[0].startswith('"Write the report": done.')
    w.advance(3 * 86400)
    out = w.reporter.progress(now=w.clock.now()).splitlines()
    assert out[0] == "No open tasks." and out[1].startswith('"Write the report": done.')


# ------------------------------------------------------------------------------------------------ the waits


@XFAIL
def test_nothing_is_waited_for_when_no_listed_task_is_being_worked_on(w: ProgressWorld, task: Message) -> None:
    w.answer(task, "done", "ok", 0)
    assert not w.reporter.work_in_flight()
    out = w.reporter.progress(wait_seconds=60)
    assert out.startswith("Nothing to wait for: no listed task is being worked on right now.\n") and w.clock.sleeps == 0


@XFAIL
def test_a_wait_returns_when_a_task_finishes(w: ProgressWorld, task: Message) -> None:
    w.clock.on_sleep(2, lambda: w.answer(task, "done", "ok", 0))
    out = w.reporter.progress(wait_seconds=60)
    assert out.startswith('Changed after waiting 4s: "Write the report": working -> done\n') and w.clock.sleeps == 2


@XFAIL
def test_a_wait_returns_for_something_new_that_needs_the_user(w: ProgressWorld, task: Message) -> None:
    w.clock.on_sleep(1, lambda: setattr(w.queue, "entries", [("m1", "Needs you: question (message m1)")]))
    assert w.reporter.progress(wait_seconds=60).startswith("Changed after waiting 2s: new item for you: Needs you: question (message m1)\n")


@XFAIL
def test_a_wait_ends_when_the_time_is_up(w: ProgressWorld, task: Message) -> None:
    out = w.reporter.progress(wait_seconds=6)
    assert out.startswith("Waited 6s: no task finished, got blocked or stalled, and nothing new needs you. Call progress(wait_seconds=...) again to keep waiting.\n")
    assert w.clock.slept == [2.0, 2.0, 2.0]


@XFAIL
def test_a_wait_is_capped(w: ProgressWorld, task: Message) -> None:
    out = w.reporter.progress(wait_seconds=5000)
    assert out.startswith("Waited 15m:") and sum(w.clock.slept) == WAIT_MAX


@XFAIL
def test_a_wait_stops_when_nothing_can_run_any_more(w: ProgressWorld, task: Message) -> None:
    w.use_run("ceo")
    read(w, "ceo")
    w.answer(task, "blocked", "Out of budget for the rework.", 0)
    w.write(ROOT, "ceo", "Here are more runs.", "3 more", 3)  # blocked, but its lead can run: the wait waits
    assert w.reporter.work_in_flight()
    w.clock.on_sleep(1, lambda: read(w, "ceo"))  # the lead reads the grant and does nothing with it
    out = w.reporter.progress(wait_seconds=60)
    assert out.startswith("Stopped after waiting 4s: nothing in the org can run any more and no task finished. It needs a decision, budget or a restart (see below).\n")


@XFAIL
def test_a_blocked_task_nobody_can_run_is_not_in_flight(w: ProgressWorld, task: Message) -> None:
    read(w, "ceo")
    w.answer(task, "blocked", "Out of budget.", 0)
    assert not w.reporter.work_in_flight() and not w.reporter.work_in_flight(task.id)


@XFAIL
def test_work_in_flight_of_one_task(w: ProgressWorld, task: Message) -> None:
    other = w.delegate(ROOT, "ceo/eng", "Other", 2)
    w.answer(other, "done", "ok", 0)
    assert w.reporter.work_in_flight() and w.reporter.work_in_flight(task.id) and not w.reporter.work_in_flight(other.id)


# ------------------------------------------------------------------------------------------------ the scheduler line


@XFAIL
def test_without_a_scheduler_a_wait_returns_at_once_and_says_so(w: ProgressWorld, task: Message) -> None:
    out = w.reporter.describe_progress(None, 600)
    assert out.startswith("Not waiting: no scheduler is running, so nothing will change. ") and "working" in out
    assert out.splitlines()[-1] == "scheduler: stopped - open tasks do not move until it is started (start() or `orgmcp run`)"
    assert w.clock.sleeps == 0


@XFAIL
def test_a_scheduler_that_runs_lets_the_wait_through(w: ProgressWorld, task: Message) -> None:
    w.scheduler.current = SchedulerState("running", 1, "x")
    w.clock.on_sleep(1, lambda: w.answer(task, "done", "ok", 0))
    out = w.reporter.describe_progress(None, 30)
    assert out.startswith("Changed after waiting 2s:") and out.endswith("\nscheduler: running (pid 1, since x)")


@XFAIL
def test_no_open_task_and_no_scheduler_is_just_the_line(w: ProgressWorld) -> None:
    assert w.reporter.describe_progress() == "No open tasks.\nscheduler: stopped"


@XFAIL
def test_a_stopped_scheduler_with_a_blocked_task_that_could_run_does_not_wait(w: ProgressWorld, task: Message) -> None:
    w.use_run("ceo")
    read(w, "ceo")
    w.answer(task, "blocked", "Out of budget.", 0)
    w.write(ROOT, "ceo", "Here are more runs.", "3 more", 3)
    out = w.reporter.describe_progress(None, 600)
    assert out.startswith("Not waiting: no scheduler is running, so nothing will change. ")
    assert "agents have work they could do" in out.splitlines()[-1] and "start()" in out.splitlines()[-1]


@XFAIL
def test_when_everything_waits_for_the_user_the_line_says_so_and_does_not_wait(w: ProgressWorld, task: Message) -> None:
    w.waiting.waiting = Waiting('waiting on you: "Write the report" needs budget (ceo out of runs)', 'Your options: send(to="ceo", ...)')
    w.scheduler.open_tasks = True
    out = w.reporter.describe_progress(None, 300)
    assert out.startswith("Not waiting: nothing can progress without you. ")
    last = out.splitlines()[-1]
    assert last.startswith('scheduler: stopped (waiting on you: "Write the report" needs budget (ceo out of runs)) - nothing moves until you act. ')
    assert last.endswith('Your options: send(to="ceo", ...)')


@XFAIL
def test_while_the_scheduler_runs_the_waiting_user_is_told_it_exits_by_itself(w: ProgressWorld, task: Message) -> None:
    w.waiting.waiting = Waiting('waiting on you: "Write the report" needs budget', "Your options: x.")
    w.scheduler.current = SchedulerState("running", 1, "x")
    out = w.reporter.describe_progress()
    assert out.endswith(
        'scheduler: running (pid 1, since x) - waiting on you: "Write the report" needs budget. Your options: x. A scheduler started with until_done exits by itself soon.'
    )
    assert not out.startswith("Not waiting")


@XFAIL
def test_an_unverified_scheduler_is_neither_stopped_nor_running(w: ProgressWorld, task: Message) -> None:
    w.scheduler.current = SchedulerState("unverified", 7, "x", "not trusted")
    out = w.reporter.describe_progress(None, 30)
    assert not out.startswith("Not waiting") and "scheduler: unknown" in out.splitlines()[-1]
