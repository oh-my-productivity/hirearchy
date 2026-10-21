"""The fakes of ``progress.testing`` do what their docstrings say (a fake that lies makes every test that uses it lie)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hirearchy.kernel import ROOT, Message
from hirearchy.kernel.testing import FakeClock
from hirearchy.progress import ProgressReporter
from hirearchy.progress._ports import TeamActivity
from hirearchy.progress._ports import Snapshot, Snapshots, TaskMark
from hirearchy.progress.testing import FixedCaseTotals, FixedProgressReporter, FixedSnapshots, FixedTeamActivity, ScriptedClock, SpyProgressView
from hirearchy.reflection import ServiceReports

AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_the_fixed_reporter_answers_what_it_is_told_and_keeps_the_calls() -> None:
    fixed = FixedProgressReporter("lines", "lines\nscheduler: stopped", moving=True)
    assert isinstance(fixed, ProgressReporter)
    assert fixed.progress("t", AT, wait_seconds=3) == "lines" and fixed.describe_progress("t", 4) == "lines\nscheduler: stopped" and fixed.work_in_flight("t")
    assert fixed.calls == [("progress", "t", AT, 3), ("describe_progress", "t", None, 4), ("work_in_flight", "t", None, 0)]


def test_the_fixed_reporter_describes_with_its_text_when_not_told_otherwise() -> None:
    assert FixedProgressReporter("lines").describe_progress() == "lines" and not FixedProgressReporter().work_in_flight()


def test_the_spy_view_answers_and_keeps_what_it_was_asked() -> None:
    spy = SpyProgressView("x")
    assert spy.progress("t", AT, wait_seconds=5) == "x" and spy.progress() == "x"
    assert spy.asked == [("t", AT, 5), (None, None, 0)] and spy.kwargs == {"wait_seconds": 0}


def test_the_fixed_snapshots_are_what_they_are_told_and_keep_what_was_asked() -> None:
    mark = Snapshot({"t": TaskMark("working", "T", "working")}, {}, frozenset())
    fixed = FixedSnapshots(mark)
    assert isinstance(fixed, Snapshots) and fixed.snapshot("t") is mark and fixed.snapshot(None) is mark and fixed.asked == ["t", None]
    assert FixedSnapshots().snapshot(None) == Snapshot({}, {}, frozenset())


def test_the_fixed_activity_is_the_newest_time_of_the_team() -> None:
    fixed = FixedTeamActivity({"ceo": AT, "ceo/eng": AT + timedelta(minutes=1)})
    assert isinstance(fixed, TeamActivity)
    assert fixed.newest(["ceo"]) == AT and fixed.newest(["ceo", "ceo/eng", "ops"]) == AT + timedelta(minutes=1) and fixed.newest(["ops"]) is None
    assert FixedTeamActivity().newest(["ceo"]) is None


def test_the_fixed_totals_are_per_task() -> None:
    totals = FixedCaseTotals({"a": "case total: 1"})
    assert isinstance(totals, ServiceReports)
    assert totals.case_total(Message(sender=ROOT, to="ceo", type="task", body="", id="a")) == "case total: 1"
    assert totals.case_total(Message(sender=ROOT, to="ceo", type="task", body="", id="b")) == "" and totals.services_text("ceo") == ""


def test_the_scripted_clock_sleeps_by_moving_the_time_and_runs_the_action_of_that_sleep() -> None:
    clock = ScriptedClock(FakeClock())
    ran: list[int] = []
    clock.on_sleep(2, lambda: ran.append(clock.sleeps))
    for seconds in (1.0, 2.0, 3.0):
        clock.sleep(seconds)
    assert ran == [2] and clock.sleeps == 3 and clock.slept == [1.0, 2.0, 3.0] and clock.monotonic() == 6.0
