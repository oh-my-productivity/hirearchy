"""``LogRunCounts``: the runs a team made for a root task, against everything root put into the team for it."""

from __future__ import annotations

from orgmcp.kernel import ROOT, Message
from orgmcp.progress._ports import RunCounts
from orgmcp.progress._counts import LogRunCounts
from orgmcp.progress.testing import ProgressWorld


TEAM = ["ceo", "ceo/eng"]


def counts(w: ProgressWorld) -> LogRunCounts:
    return LogRunCounts(w.mail, w.runs)


def text(w: ProgressWorld, task: Message, result: Message | None = None) -> str:
    return counts(w).runs_text(task, result, TEAM)


def test_it_is_a_run_counter(w: ProgressWorld) -> None:
    assert isinstance(counts(w), RunCounts)


def test_no_runs_against_the_budget_of_the_task(w: ProgressWorld, task: Message) -> None:
    assert text(w, task) == "runs 0 of 8"


def test_every_run_of_the_team_counts(w: ProgressWorld, task: Message) -> None:
    for addr in ("ceo", "ceo", "ceo/eng"):
        w.use_run(addr)
    assert text(w, task) == "runs 3 of 8"


def test_runs_from_before_the_task_are_not_its_own(w: ProgressWorld) -> None:
    w.hire("ops")
    w.use_run("ceo")
    task = w.delegate(ROOT, "ceo", "Later", 4)
    w.use_run("ceo")
    assert text(w, task) == "runs 1 of 4"


def test_grants_of_root_to_the_team_add_to_the_budget_but_not_to_others(w: ProgressWorld, task: Message) -> None:
    w.hire("ops")
    w.write(ROOT, "ceo/eng", "More", "3 more", 3)
    w.write(ROOT, "ops", "Not ours", "5 more", 5)
    w.write("ceo", "ceo/eng", "Not root's", "1 more", 1)
    assert text(w, task) == "runs 0 of 11"


def test_a_final_result_ends_the_window_and_says_how_many_runs_came_back(w: ProgressWorld, task: Message) -> None:
    w.use_run("ceo")
    done = w.answer(task, "done", "ok", 7)
    w.use_run("ceo")  # after the result: not this task's
    w.write(ROOT, "ceo", "After", "2 more", 2)
    assert text(w, task, done) == "runs 1 of 8 (7 returned)"


def test_a_blocked_result_is_not_final_so_the_window_stays_open(w: ProgressWorld, task: Message) -> None:
    w.use_run("ceo")
    blocked = w.answer(task, "blocked", "stuck", 0)
    w.write(ROOT, "ceo", "More", "3 more", 3)
    w.use_run("ceo")
    assert text(w, task, blocked) == "runs 2 of 11"


def test_the_next_task_to_the_same_assignee_ends_the_window_early(w: ProgressWorld, task: Message) -> None:
    w.use_run("ceo")
    w.delegate(ROOT, "ceo", "Next", 4)
    w.use_run("ceo")  # the next task's run
    assert text(w, task) == "runs 1 of 8"
    assert text(w, task, w.answer(task, "done", "ok", 0)) == "runs 1 of 8"


def test_a_task_to_another_assignee_does_not_cut_the_window(w: ProgressWorld, task: Message) -> None:
    w.use_run("ceo")
    w.delegate(ROOT, "ceo/eng", "Elsewhere", 4)
    w.use_run("ceo")
    assert text(w, task) == "runs 2 of 8"
