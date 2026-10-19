"""``MailRootTasks``, ``listed`` and ``RootTaskReport``: which tasks root gave, which are listed, and the report."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orgmcp.kernel import ROOT, Message
from orgmcp.progress._lines import CaseTaskLines
from orgmcp.progress._listing import RECENT, MailRootTasks, listed
from orgmcp.progress._ports import ProgressText, RootTasks
from orgmcp.progress._render import RootTaskReport
from orgmcp.progress.testing import ProgressWorld

from ._support import XFAIL


AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def result_at(when: datetime, status: str = "done") -> Message:
    return Message(sender="ceo", to=ROOT, type="result", body="", status=status, id=f"{when:%Y%m%dT%H%M%S%f}-ceo-aaaa")


def test_the_recent_window_is_a_day() -> None:
    assert RECENT == timedelta(hours=24)


def test_it_is_a_source_of_root_tasks(w: ProgressWorld) -> None:
    assert isinstance(MailRootTasks(w.mail), RootTasks)


@XFAIL
def test_root_tasks_are_the_tasks_root_sent_and_their_latest_results(w: ProgressWorld, task: Message) -> None:
    other = w.delegate(ROOT, "ceo/eng", "Other", 2)
    w.write(ROOT, "ceo", "A note", "not a task", 0)
    w.answer(task, "blocked", "stuck", 0)
    final = w.answer(task, "done", "ok", 0)
    roots = MailRootTasks(w.mail)
    assert [t.id for t in roots.tasks()] == [task.id, other.id]
    assert {k: v.id for k, v in roots.latest_results().items()} == {task.id: final.id}


@XFAIL
def test_open_and_blocked_tasks_are_always_listed(w: ProgressWorld) -> None:
    assert listed(None, AT) and listed(result_at(AT - timedelta(days=30), "blocked"), AT)


@XFAIL
def test_a_finished_task_is_listed_for_a_day_after_it_finished() -> None:
    result = result_at(AT)
    assert listed(result, AT + RECENT) and not listed(result, AT + RECENT + timedelta(seconds=1))
    assert listed(Message(sender="ceo", to=ROOT, type="result", body="", status="done", id="not-a-time"), AT)  # no time in the id: nothing to age


def report(w: ProgressWorld) -> RootTaskReport:
    from orgmcp.progress._counts import LogRunCounts
    from orgmcp.progress._states import MailTaskStates
    from orgmcp.progress._teams import AgentTaskTeams

    lines = CaseTaskLines(
        AgentTaskTeams(w.agents), MailTaskStates(w.mail, w.pauses, w.tasks), LogRunCounts(w.mail, w.runs), w.activity, w.history, w.totals,
    )
    return RootTaskReport(MailRootTasks(w.mail), lines, w.queue, w.clock)


def test_it_is_a_text(w: ProgressWorld) -> None:
    assert isinstance(report(w), ProgressText)


@XFAIL
def test_open_tasks_come_first_and_old_finished_ones_are_dropped(w: ProgressWorld, task: Message) -> None:
    old = w.delegate(ROOT, "ceo/eng", "Old", 2)
    w.answer(old, "done", "ok", 0)
    w.advance(3 * 86400)
    fresh = w.delegate(ROOT, "ceo/eng", "Fresh", 2)
    w.answer(fresh, "done", "ok", 0)
    titles = [line.split(":")[0] for line in report(w).render(None, w.clock.now()).splitlines()]
    assert titles == ['"Write the report"', '"Fresh"']


@XFAIL
def test_nothing_open_shows_the_last_finished_one(w: ProgressWorld, task: Message) -> None:
    w.answer(task, "done", "ok", 0)
    first = w.delegate(ROOT, "ceo/eng", "Second", 2)
    w.answer(first, "done", "ok", 0)
    w.advance(3 * 86400)
    out = report(w).render(None, w.clock.now()).splitlines()
    assert out[0] == "No open tasks." and out[1].startswith('"Second": done.') and len(out) == 2


@XFAIL
def test_the_queue_follows_the_tasks(w: ProgressWorld, task: Message) -> None:
    w.queue.entries = [("m1", "Needs you: one (message m1)")]
    assert report(w).render(task.id, None).splitlines()[1:] == ["Needs you: one (message m1)"]
