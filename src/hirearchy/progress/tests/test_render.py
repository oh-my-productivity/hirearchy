"""``MailRootTasks``, ``listed`` and ``RootTaskReport``: which tasks root gave, which are listed, and the report."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from hirearchy.kernel import ROOT, Message, OrgError
from hirearchy.progress._lines import CaseTaskLines
from hirearchy.progress._listing import RECENT, MailRootTasks, listed
from hirearchy.progress._ports import ProgressText, RootTasks
from hirearchy.progress._render import RootTaskReport
from hirearchy.progress.testing import ProgressWorld
from hirearchy.reflection import DeliverableChecks, DeliverableFinding, deliverables_note


AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def result_at(when: datetime, status: str = "done") -> Message:
    return Message(sender="ceo", to=ROOT, type="result", body="", status=status, id=f"{when:%Y%m%dT%H%M%S%f}-ceo-aaaa")


def test_the_recent_window_is_a_day() -> None:
    assert RECENT == timedelta(hours=24)


def test_it_is_a_source_of_root_tasks(w: ProgressWorld) -> None:
    assert isinstance(MailRootTasks(w.mail), RootTasks)


def test_root_tasks_are_the_tasks_root_sent_and_their_latest_results(w: ProgressWorld, task: Message) -> None:
    other = w.delegate(ROOT, "ceo/eng", "Other", 2)
    w.write(ROOT, "ceo", "A note", "not a task", 0)
    w.answer(task, "blocked", "stuck", 0)
    final = w.answer(task, "done", "ok", 0)
    roots = MailRootTasks(w.mail)
    assert [t.id for t in roots.tasks()] == [task.id, other.id]
    assert {k: v.id for k, v in roots.latest_results().items()} == {task.id: final.id}


def test_open_and_blocked_tasks_are_always_listed(w: ProgressWorld) -> None:
    assert listed(None, AT) and listed(result_at(AT - timedelta(days=30), "blocked"), AT)


def test_a_finished_task_is_listed_for_a_day_after_it_finished() -> None:
    result = result_at(AT)
    assert listed(result, AT + RECENT) and not listed(result, AT + RECENT + timedelta(seconds=1))
    assert listed(Message(sender="ceo", to=ROOT, type="result", body="", status="done", id="not-a-time"), AT)  # no time in the id: nothing to age


def report(w: ProgressWorld, checks: DeliverableChecks | None = None) -> RootTaskReport:
    from hirearchy.progress._counts import LogRunCounts
    from hirearchy.progress._states import MailTaskStates
    from hirearchy.progress._teams import AgentTaskTeams

    lines = CaseTaskLines(
        AgentTaskTeams(w.agents), MailTaskStates(w.mail, w.pauses, w.tasks), LogRunCounts(w.mail, w.runs), w.activity, w.history, w.totals, w.mail,
    )
    return RootTaskReport(MailRootTasks(w.mail), lines, w.queue, w.clock, checks or w.deliverables)


def test_it_is_a_text(w: ProgressWorld) -> None:
    assert isinstance(report(w), ProgressText)


def test_open_tasks_come_first_and_old_finished_ones_are_dropped(w: ProgressWorld, task: Message) -> None:
    old = w.delegate(ROOT, "ceo/eng", "Old", 2)
    w.answer(old, "done", "ok", 0)
    w.advance(3 * 86400)
    fresh = w.delegate(ROOT, "ceo/eng", "Fresh", 2)
    w.answer(fresh, "done", "ok", 0)
    titles = [line.split(":")[0] for line in report(w).render(None, w.clock.now()).splitlines()]
    assert titles == ['"Write the report"', '"Fresh"']


def test_nothing_open_shows_the_last_finished_one(w: ProgressWorld, task: Message) -> None:
    w.answer(task, "done", "ok", 0)
    first = w.delegate(ROOT, "ceo/eng", "Second", 2)
    w.answer(first, "done", "ok", 0)
    w.advance(3 * 86400)
    out = report(w).render(None, w.clock.now()).splitlines()
    assert out[0] == "No open tasks." and out[1].startswith('"Second": done.') and len(out) == 2


def test_the_queue_follows_the_tasks(w: ProgressWorld, task: Message) -> None:
    w.queue.entries = [("m1", "Needs you: one (message m1)")]
    assert report(w).render(task.id, None).splitlines()[1:] == ["Needs you: one (message m1)"]


# ------------------------------------------------------------------------------------------------------------------------ the deliverable note (P3, design 6.5)


def found(name: str = "memo.md", kind: str = "unknown", service: str = "brief", folder: str = "/tmp/deliverables") -> DeliverableFinding:
    return DeliverableFinding(folder=folder, services=(service,), name=name, kind=kind)


def service_task(w: ProgressWorld, service: str = "brief") -> Message:
    return w.post(Message(sender=ROOT, to="ceo", type="task", title=f"{service}: ai", body="goal", budget=5, service=service, playbook=1))


def test_root_progress_appends_the_deliverable_note_before_the_human_queue(w: ProgressWorld, task: Message) -> None:
    w.deliverables.put(ROOT, found())
    w.queue.entries = [("m1", "Needs you: one (message m1)")]
    lines = report(w).render(None, w.clock.now()).splitlines()
    assert lines[0].startswith('"Write the report"')
    assert lines[1:-1] == deliverables_note([found()]).splitlines() and lines[1].startswith('Deliverable folder "/tmp/deliverables" (service `brief`)')
    assert lines[-1] == "Needs you: one (message m1)"
    nothing = report(w, type(w.deliverables)()).render(None, w.clock.now())
    assert "Deliverable" not in nothing  # no findings, no note


def test_the_note_follows_a_report_with_no_open_task(w: ProgressWorld) -> None:
    w.deliverables.put(ROOT, found())
    assert report(w).render(None, w.clock.now()).splitlines()[0] == "No open tasks."
    assert "never written by the team" in report(w).render(None, w.clock.now())


def test_progress_of_a_service_task_shows_only_its_group(w: ProgressWorld) -> None:
    w.deliverables.put(ROOT, found("a.md", service="brief"), found("b.md", service="other", folder="/tmp/other"))
    brief, other = service_task(w, "brief"), service_task(w, "other")
    for task, shown, hidden in ((brief, "a.md", "b.md"), (other, "b.md", "a.md")):
        out = report(w).render(task.id, None)
        assert f'"{shown}"' in out and f'"{hidden}"' not in out
    both = report(w).render(None, w.clock.now())
    assert '"a.md"' in both and '"b.md"' in both  # the list shows every service root requests


def test_a_one_off_task_shows_no_block(w: ProgressWorld, task: Message) -> None:
    w.deliverables.put(ROOT, found())
    assert "Deliverable" not in report(w).render(task.id, None)  # a goal given with `delegate` has no service: no folder to speak of
    assert "Deliverable" in report(w).render(None, w.clock.now())


class RaisingChecks(DeliverableChecks):
    def __init__(self, error: Exception) -> None:
        self._error = error

    def findings(self, actor: str, service: str | None = None) -> list[DeliverableFinding]:
        raise self._error


def test_a_findings_error_drops_the_note(w: ProgressWorld, task: Message) -> None:
    w.queue.entries = [("m1", "Needs you: one (message m1)")]
    for error in (OrgError("a contract cannot be read"), OSError(5, "I/O error")):
        out = report(w, RaisingChecks(error)).render(None, w.clock.now()).splitlines()
        assert out[0].startswith('"Write the report"') and out[-1] == "Needs you: one (message m1)" and len(out) == 2  # the rest of the report is whole
    with pytest.raises(ValueError):  # anything else is a bug: not hidden
        report(w, RaisingChecks(ValueError("a bug"))).render(None, w.clock.now())
