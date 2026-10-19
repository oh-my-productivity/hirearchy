"""The steps of a pass of the loop, each on its own."""

from __future__ import annotations

from datetime import datetime, timezone

from orgmcp.kernel.testing import FakeClock
from orgmcp.review import Note, Review
from orgmcp.review.testing import ScriptedHealthReviewer
from orgmcp.scheduler._phases import (
    FailureLedgerRepair, FundedResume, GuardedPhase, OrphanCheck, ReapPhase, ReviewCheck, RunLaunch, StallCheck,
)
from orgmcp.scheduler._run import Standing
from orgmcp.scheduler.testing import (
    CatchingGuard, RecordingConsole, RecordingPhase, RecordingReaper, RecordingSettler, RecordingStarter, ScriptedLadder, lifecycle_world,
)
from orgmcp.eligibility.testing import MemoryFailureCounter

from ._support import red

pytestmark = red

STANDING = Standing({}, set())


def test_a_malformed_failure_ledger_is_repaired_and_said() -> None:
    counter, console = MemoryFailureCounter(), RecordingConsole()
    FailureLedgerRepair(counter, console).run(STANDING, None)
    assert console.lines == []
    counter.text = "[]"
    FailureLedgerRepair(counter, console).run(STANDING, None)
    assert console.lines == ["repaired malformed .runtime/failures.json"]


def test_reaping_is_the_reapers_job_on_the_runs_in_flight() -> None:
    reaper = RecordingReaper()
    ReapPhase(reaper).run(STANDING, None)
    assert reaper.reaped == 1


def test_orphans_are_looked_at_only_while_some_agent_is_blocked() -> None:
    settler = RecordingSettler()
    phase = OrphanCheck(settler)
    phase.run(Standing({}, set()), None)
    assert settler.calls == 0
    blocked = {"ceo"}
    phase.run(Standing({}, blocked), None)
    assert settler.calls == 1


def test_an_agent_paused_for_budget_whose_budget_is_back_is_resumed_and_said() -> None:
    w = lifecycle_world()
    w.hire("ceo", 3)
    w.hire("ops", 0)
    w.hire("dev", 2)
    w.pauses.pause("ceo", "budget")
    w.pauses.pause("ops", "budget")  # still no runs
    w.pauses.pause("dev", "failures")  # a pause of another kind is not ours to lift
    FundedResume(w.access.agents, w.pauses, w.budgets, w.console).run(STANDING, None)
    assert (w.pauses.paused("ceo"), w.pauses.paused("ops"), w.pauses.paused("dev")) == (None, "budget", "failures")
    assert w.console.lines == ["ceo: budget is back, resumed"]
    assert [(e["agent"], e["actor"], e["reason"]) for e in w.events_of("agent.resume")] == [("ceo", "runtime", "budget is back")]


def test_runs_are_launched_while_the_cap_allows_and_told_who_is_blocked_and_the_cap() -> None:
    starter = RecordingStarter()
    RunLaunch(starter).run(Standing({}, {"ops"}, can_start=True), 4)
    RunLaunch(starter).run(Standing({}, set(), can_start=False), 4)
    assert starter.launched == [({"ops"}, 4)]


def test_the_stall_ladder_is_climbed_and_each_line_said() -> None:
    ladder, console = ScriptedLadder("ceo: reminded about open task t1", "ceo: stalled on t1, told root"), RecordingConsole()
    StallCheck(ladder, console).run(STANDING, None)
    assert ladder.checks == 1 and console.lines == ["ceo: reminded about open task t1", "ceo: stalled on t1, told root"]


def test_a_review_that_is_due_is_asked_by_the_cadence_clock_and_said_when_it_wrote() -> None:
    clock, console = FakeClock(), RecordingConsole()
    at = datetime.fromtimestamp(clock.time(), timezone.utc)
    done = Review(at=at, runs=0, flagged=2, notes=[Note("ceo", "t", "b"), Note("root", "t", "b")])
    reviewer = ScriptedHealthReviewer(done, due=done)
    ReviewCheck(reviewer, clock, console).run(STANDING, None)
    (kind, asked, _), = reviewer.calls
    assert kind == "review_if_due" and asked is not None and asked.tzinfo is not None and abs((asked - at).total_seconds()) < 1
    assert console.lines == ["health review: 2 flagged, told ceo, root"]


def test_a_review_that_is_not_due_or_wrote_nothing_says_nothing() -> None:
    clock, console = FakeClock(), RecordingConsole()
    quiet = Review(at=clock.now(), runs=0, flagged=1)
    for reviewer in (ScriptedHealthReviewer(quiet, due=None), ScriptedHealthReviewer(quiet, due=quiet)):
        ReviewCheck(reviewer, clock, console).run(STANDING, None)
    assert console.lines == []


def test_a_guarded_phase_is_run_by_the_guard_under_its_name() -> None:
    guard, journal = CatchingGuard(), list[str]()
    inner = RecordingPhase("inner", journal)
    GuardedPhase("stall check", inner, guard).run(STANDING, 7)
    assert guard.phases == ["stall check"] and journal == ["inner"] and inner.seen == [(STANDING, 7)]


def test_a_fault_in_a_guarded_phase_goes_no_further() -> None:
    guard = CatchingGuard()
    GuardedPhase("stall check", RecordingPhase("inner", [], fail=RuntimeError("kaput")), guard).run(STANDING, None)
    assert guard.errors == [("stall check", "RuntimeError: kaput")]
