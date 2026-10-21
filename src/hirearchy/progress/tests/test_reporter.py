"""``DerivedProgressReporter``: progress, the scheduler line and whether anything could move, over a view and fakes of the packages it consumes."""

from __future__ import annotations

from collections.abc import Collection
from datetime import datetime, timezone

from hirearchy.attention import Waiting, WaitingOnUser
from hirearchy.attention.testing import FixedWaiting
from hirearchy.daemon import SchedulerState
from hirearchy.daemon.testing import FakeSchedulerStatus
from hirearchy.kernel import ROOT, Message
from hirearchy.progress import ProgressReporter
from hirearchy.progress._reporter import DerivedProgressReporter
from hirearchy.progress.testing import ProgressWorld, SpyProgressView


RUNNING = SchedulerState("running", 1, "x")
OPTIONS = 'Your options: send(to="ceo", ...)'


def reporter(w: ProgressWorld, view: SpyProgressView, scheduler: FakeSchedulerStatus, waiting: WaitingOnUser | None = None) -> DerivedProgressReporter:
    return DerivedProgressReporter(view, w.snapshots, scheduler, waiting or FixedWaiting(), w.tasks)


def test_it_is_a_progress_reporter(w: ProgressWorld) -> None:
    assert isinstance(reporter(w, SpyProgressView(), FakeSchedulerStatus()), ProgressReporter)


def test_progress_is_the_view(w: ProgressWorld) -> None:
    spy = SpyProgressView("lines")
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert reporter(w, spy, FakeSchedulerStatus()).progress("t", at, wait_seconds=5) == "lines" and spy.asked == [("t", at, 5)]


def test_a_running_scheduler_lets_the_wait_through_and_the_line_follows_the_text(w: ProgressWorld, task: Message) -> None:
    spy = SpyProgressView()
    out = reporter(w, spy, FakeSchedulerStatus(RUNNING)).describe_progress(None, 30)
    assert out == "lines\nscheduler: running (pid 1, since x)" and spy.asked == [(None, None, 30)]


def test_a_stopped_scheduler_with_open_work_does_not_wait(w: ProgressWorld, task: Message) -> None:
    spy = SpyProgressView()
    out = reporter(w, spy, FakeSchedulerStatus()).describe_progress(task.id, 600)
    assert out == (
        "Not waiting: no scheduler is running, so nothing will change. lines\n"
        "scheduler: stopped - open tasks do not move until it is started (start() or `hirearchy run`)"
    )
    assert spy.asked == [(task.id, None, 0)]


def test_without_a_wait_there_is_no_note(w: ProgressWorld, task: Message) -> None:
    out = reporter(w, SpyProgressView(), FakeSchedulerStatus()).describe_progress()
    assert out.startswith("lines\n") and out.endswith("it is started (start() or `hirearchy run`)")


def test_without_open_work_the_scheduler_line_is_bare(w: ProgressWorld) -> None:
    assert reporter(w, SpyProgressView(), FakeSchedulerStatus()).describe_progress(None, 600) == "lines\nscheduler: stopped"


def test_a_waiting_user_is_asked_only_when_root_has_open_work(w: ProgressWorld, task: Message) -> None:
    waiting = FixedWaiting(Waiting("waiting on you: x", OPTIONS))
    reporter(w, SpyProgressView(), FakeSchedulerStatus(), waiting).describe_progress()
    assert waiting.asked == [(None, (), True)]
    idle = FixedWaiting(Waiting("waiting on you: x", OPTIONS))
    answered = w.answer(task, "done", "ok", 0)
    assert answered.type == "result" and not w.tasks.outstanding(ROOT)
    reporter(w, SpyProgressView(), FakeSchedulerStatus(), idle).describe_progress()
    assert idle.asked == []


def test_a_stopped_scheduler_of_a_user_who_must_act_says_what_to_do_and_does_not_wait(w: ProgressWorld, task: Message) -> None:
    waiting = FixedWaiting(Waiting("waiting on you: x", OPTIONS))
    stopped = FakeSchedulerStatus(open_tasks=True, waiting=waiting)
    out = reporter(w, SpyProgressView(), stopped, waiting).describe_progress(None, 300)
    assert out == f"Not waiting: nothing can progress without you. lines\nscheduler: stopped (waiting on you: x) - nothing moves until you act. {OPTIONS}"


def test_a_running_scheduler_of_a_user_who_must_act_says_it_exits_by_itself(w: ProgressWorld, task: Message) -> None:
    waiting = FixedWaiting(Waiting("waiting on you: x", OPTIONS))
    out = reporter(w, SpyProgressView(), FakeSchedulerStatus(RUNNING), waiting).describe_progress(None, 300)
    assert out == f"Not waiting: nothing can progress without you. lines\nscheduler: running (pid 1, since x) - waiting on you: x. {OPTIONS} A scheduler started with until_done exits by itself soon."


def test_an_unverified_scheduler_is_not_a_running_one(w: ProgressWorld, task: Message) -> None:
    spy = SpyProgressView()
    out = reporter(w, spy, FakeSchedulerStatus(SchedulerState("unverified", 7, "x", "not trusted"))).describe_progress(None, 30)
    assert out.startswith("Not waiting: no scheduler is running, so nothing will change. lines\nscheduler: unknown") and spy.asked == [(None, None, 0)]


def test_work_in_flight_is_what_the_snapshot_says(w: ProgressWorld, task: Message) -> None:
    assert reporter(w, SpyProgressView(), FakeSchedulerStatus()).work_in_flight() is True
    w.answer(task, "done", "ok", 0)
    assert reporter(w, SpyProgressView(), FakeSchedulerStatus()).work_in_flight(task.id) is False


def test_the_blocked_agents_the_scheduler_knows_are_not_asked_of_the_waiting_user(w: ProgressWorld, task: Message) -> None:
    waiting = FixedWaiting()
    reporter(w, SpyProgressView(), FakeSchedulerStatus(), waiting).describe_progress()
    running: Collection[str] | None = waiting.asked[0][0]
    assert running is None and waiting.asked[0][1] == ()
