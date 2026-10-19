"""The parts of reaping: watching a run for its end, settling an ended run, interrupting every run at shutdown, and the pass over the table."""

from __future__ import annotations

import signal
from pathlib import Path

from orgmcp.kernel.testing import FakeClock
from orgmcp.processes.testing import FakeProcessTable
from orgmcp.scheduler._reaper import ExitWatcher, PollingRunReaper, RunSettlement, ShutdownTerminator
from orgmcp.scheduler._run import Exit, RunRecord
from orgmcp.scheduler.testing import (
    CatchingGuard, LifecycleWorld, MemoryRunRecords, NullSink, RecordingConsole, RecordingRunEvents, RecordingRunFailures, RecordingSettling,
    RecordingTerminating, ScriptedStrayWatch, ScriptedWatching, lifecycle_world,
)
from orgmcp.access.testing import StaticAccess

from ._support import ROOT_DIR, a_run, red

pytestmark = red


def watcher(timeout: float = 100.0) -> tuple[ExitWatcher, FakeProcessTable, FakeClock, StaticAccess]:
    clock = FakeClock()
    access = StaticAccess(ROOT_DIR, f"---\nrun_timeout: {timeout}\n---\n# Organization\n")
    access.put_agent("ceo", {})
    return ExitWatcher(access.agents, access.settings, clock), FakeProcessTable(clock), clock, access


def test_a_run_still_going_is_not_ended() -> None:
    watching, table, clock, _ = watcher()
    run = a_run(table, clock)
    clock.advance(99)
    assert watching.watch(run) is None and run.proc.returncode is None


def test_an_exit_is_reported_with_its_code() -> None:
    watching, table, clock, _ = watcher()
    run = a_run(table, clock)
    table.exit(run.proc.pid, 7)
    assert watching.watch(run) == Exit(7, None) and not run.killed


def test_a_run_past_the_timeout_is_killed_with_its_group_and_says_so_in_its_log() -> None:
    watching, table, clock, _ = watcher(timeout=50)
    sink = NullSink()
    run = a_run(table, clock, sink=sink)
    grandchild = table.add_member(run.proc.pid)
    clock.advance(51)
    exit = watching.watch(run)
    assert exit is not None and exit.why == "timed out: killed after 50s" and exit.code < 0
    assert (run.killed, run.timed_out) == (True, True) and sink.text == "\n# killed after 50s timeout\n"
    assert not table.is_alive(grandchild) and ("group", run.proc.pid, signal.SIGKILL) in table.signals


def test_the_timeout_is_measured_by_the_clock_it_is_given() -> None:
    watching, table, clock, _ = watcher(timeout=50)
    run = a_run(table, clock)
    other = FakeClock()
    other.advance(10_000)  # some other clock (the cadence of the loop) says it is long past: it is not asked
    assert watching.watch(run) is None
    clock.advance(51)
    assert watching.watch(run) is not None


def test_a_run_of_a_retired_agent_is_killed_and_says_so() -> None:
    watching, table, clock, access = watcher()
    sink = NullSink()
    run = a_run(table, clock, "gone", sink)
    exit = watching.watch(run)
    assert exit is not None and exit.why == "killed: the agent was retired during its run" and run.killed and not run.timed_out
    assert sink.text == "\n# killed: the agent was retired during its run\n" and access.agents.exists("ceo")


def settlement(w: LifecycleWorld) -> tuple[RunSettlement, RecordingRunFailures, RecordingRunEvents]:
    failures, events = RecordingRunFailures(), RecordingRunEvents()
    return RunSettlement(w.access.agents, w.box, failures, w.snapshots, events, w.console, w.ports.layout), failures, events


def an_ended_run(w: LifecycleWorld) -> RunRecord:
    w.hire("ceo")
    w.mail_to("ceo")
    w.box.begin("ceo")
    return a_run(w.table, w.clock, "ceo")


def test_a_successful_run_finishes_its_batch_clears_the_failures_and_is_committed() -> None:
    w = lifecycle_world()
    settling, failures, events = settlement(w)
    run = an_ended_run(w)
    settling.settle(run, Exit(0), 12.4)
    assert w.box.messages("ceo", "inflight") == [] and events.calls == [("ended", "ceo", 0)] and failures.cleared_agents == ["ceo"]
    assert w.console.lines == ["ceo: run finished in 12s"]
    assert w.snapshots.commits == ["ceo: run ok, 1 message(s) [ceo/runs/20260101T000000000000.log]"]


def test_a_failed_run_gives_its_batch_back_and_counts_a_failure() -> None:
    w = lifecycle_world()
    settling, failures, events = settlement(w)
    run = an_ended_run(w)
    settling.settle(run, Exit(3), 1.0)
    assert w.box.messages("ceo", "inbox") != [] and failures.failed_runs == [("ceo", run.log, ())] and events.calls == [("ended", "ceo", 3)]
    assert w.snapshots.commits == ["ceo: run failed (3), 1 message(s) [ceo/runs/20260101T000000000000.log]"] and w.console.lines == []


def test_the_reason_the_scheduler_ended_a_run_is_the_error_of_its_event() -> None:
    w = lifecycle_world()
    settling, _, events = settlement(w)
    run = an_ended_run(w)
    settling.settle(run, Exit(-9, "timed out: killed after 5s"), 5.0)
    assert events.calls == [("ended", "ceo", "timed out: killed after 5s")]


def test_a_run_that_ended_after_its_agent_was_retired_has_nothing_to_settle() -> None:
    w = lifecycle_world()
    settling, failures, events = settlement(w)
    run = a_run(w.table, w.clock, "gone")
    settling.settle(run, Exit(1), 2.0)
    assert events.calls == [("ended", "gone", "agent retired during its run")] and failures.failed_runs == [] and failures.cleared_agents == []
    assert w.console.lines == ["gone: was retired during its run (exit 1); nothing to settle"]
    assert w.snapshots.commits == ["gone: run ended after retirement (exit 1)"]
    settling.settle(run, Exit(0), 2.0)
    assert events.calls[-1] == ("ended", "gone", 0)


def test_shutdown_interrupts_every_run_gives_the_batches_back_and_empties_the_table() -> None:
    w = lifecycle_world()
    w.hire("ceo")
    w.mail_to("ceo")
    w.box.begin("ceo")
    sink, events, records = NullSink(), RecordingRunEvents(), MemoryRunRecords()
    run = a_run(w.table, w.clock, "ceo", sink)
    child = w.table.add_member(run.proc.pid)
    w.table.ignore_term(run.proc.pid)
    runs = {"ceo": run}
    records.records["ceo"] = run
    ShutdownTerminator(w.box, events, records).terminate_all(runs)
    assert runs == {} and not w.table.is_alive(child) and run.killed and sink.text == "\n# interrupted by scheduler shutdown\n" and sink.closed
    assert w.box.messages("ceo", "inbox") != [] and events.calls == [("ended", "ceo", "interrupted by scheduler shutdown")]
    assert records.records == {} and w.table.signals[0][2] == signal.SIGTERM


def test_a_pass_settles_only_the_runs_that_ended_and_forgets_them() -> None:
    clock, table = FakeClock(), FakeProcessTable()
    done, going = a_run(table, clock, "a"), a_run(table, clock, "b")
    records, strays, settling, guard = MemoryRunRecords(), ScriptedStrayWatch(), RecordingSettling(), CatchingGuard()
    records.records.update(a=done, b=going)
    clock.advance(30)
    reaper = PollingRunReaper(ScriptedWatching({"a": Exit(0)}), records, guard, strays, settling, clock, RecordingTerminating())
    runs = {"a": done, "b": going}
    reaper.reap(runs)
    assert list(runs) == ["b"] and records.records == {"b": going} and strays.checked == ["a"]
    assert [s[:2] for s in settling.settled] == [("a", Exit(0))] and abs(settling.settled[0][2] - 30.0) < 0.01
    assert done.logf.closed is True and done.logf.text == "\n# exit 0 after 30s\n"  # type: ignore[attr-defined]


def test_a_stray_check_or_registry_that_fails_never_stops_the_settling() -> None:
    clock, table = FakeClock(), FakeProcessTable()
    run = a_run(table, clock, "a")
    records, strays, settling, guard = MemoryRunRecords(), ScriptedStrayWatch(), RecordingSettling(), CatchingGuard()
    strays.fail_after, records.fail = OSError("boom"), OSError("full")
    PollingRunReaper(ScriptedWatching({"a": Exit(1)}), records, guard, strays, settling, clock, RecordingTerminating()).reap({"a": run})
    assert guard.errors == [("stray check", "OSError: boom"), ("run record", "OSError: full")] and [s[0] for s in settling.settled] == ["a"]


def test_terminate_all_is_the_terminators() -> None:
    terminating = RecordingTerminating()
    PollingRunReaper(ScriptedWatching(), MemoryRunRecords(), CatchingGuard(), ScriptedStrayWatch(), RecordingSettling(), FakeClock(), terminating).terminate_all({})
    assert terminating.calls == 1 and Path("/") == Path("/")
