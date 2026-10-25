"""Becoming the scheduler of an organization, and letting go of it."""

from __future__ import annotations

import pytest

from hirearchy.daemon.testing import MemoryExitMarker, MemorySchedulerLock
from hirearchy.kernel import OrgError
from hirearchy.kernel.testing import FakeClock, ListEventSink
from hirearchy.access.testing import StaticAccess
from hirearchy.processes.testing import FakeProcessTable
from hirearchy.scheduler._events import SchedulerEvents, SessionAnnouncer
from hirearchy.scheduler._session import BatchRecovery, ClaimedSession, ProcessClaim
from hirearchy.scheduler.testing import (
    RecordingClaim, RecordingConsole, RecordingReaper, RecordingRecovery, RecordingSessionEvents, RecordingSettler, lifecycle_world,
)
from hirearchy.snapshots.testing import MemoryIgnoreList
from hirearchy.telemetry.testing import MemoryProcessLabel

from ._support import ROOT_DIR, a_run


def test_taking_the_claim_names_the_process_takes_the_pidfile_forgets_the_last_exit_and_ignores_the_runtime_files() -> None:
    table, label, marker, ignore = FakeProcessTable(own_pid=4321), MemoryProcessLabel(), MemoryExitMarker("old reason\n"), MemoryIgnoreList()
    lock = MemorySchedulerLock(table)
    claim = ProcessClaim(label, lock, marker, ignore)
    claim.take()
    assert label.get() == "scheduler" and lock.text == "4321" and marker.text is None and ".runtime/running.json" in (ignore.text or "")
    claim.give_up()
    assert lock.text is None


def test_a_claim_is_refused_while_another_scheduler_lives_and_nothing_else_happens() -> None:
    table = FakeProcessTable()
    other = table.add(7000)
    label, marker, ignore = MemoryProcessLabel(), MemoryExitMarker("old reason\n"), MemoryIgnoreList()
    claim = ProcessClaim(label, MemorySchedulerLock(table, str(other)), marker, ignore)
    with pytest.raises(OrgError, match="already running"):
        claim.take()
    assert marker.text == "old reason\n" and ignore.text is None


def test_the_start_and_the_exit_are_events_of_the_scheduler() -> None:
    sink = ListEventSink()
    access = StaticAccess(ROOT_DIR, "---\nmax_parallel: 3\n---\n# Organization\n")
    events = SessionAnnouncer(SchedulerEvents(sink), access.settings, lambda: "9.9")
    events.started("until_done", 5)
    events.exited("x" * 700, 4)
    start, end = sink.events
    assert (start.kind, start.proc, start.actor, start.fields) == ("scheduler.start", "scheduler", "runtime", {"mode": "until_done", "max_runs": 5, "max_parallel": 3, "version": "9.9"})
    assert end.kind == "scheduler.exit" and end.fields["runs_started"] == 4 and len(str(end.fields["reason"])) == 500


def test_interrupted_batches_are_returned_and_said() -> None:
    w = lifecycle_world()
    w.hire("ceo", 3)
    w.mail_to("ceo")
    w.box.begin("ceo")  # a run began and the scheduler died
    console = RecordingConsole()
    BatchRecovery(w.box, console).recover()
    assert console.lines == ["recovered interrupted run of ceo"] and w.box.messages("ceo", "inflight") == []
    BatchRecovery(w.box, console).recover()
    assert len(console.lines) == 1


def test_opening_takes_the_claim_announces_settles_the_orphans_and_recovers_in_that_order() -> None:
    journal: list[str] = []
    session = ClaimedSession(RecordingClaim(journal), RecordingSessionEvents(journal), RecordingSettler(journal, blocks={"ceo"}), RecordingRecovery(journal), RecordingReaper(journal))
    blocked: set[str] = set()
    session.open("until_idle", 3, {}, blocked)
    assert journal == ["take", "started", "settle", "recover"] and blocked == {"ceo"}


def test_a_refused_claim_stops_the_opening() -> None:
    journal: list[str] = []
    claim = RecordingClaim(journal)
    claim.fail = OrgError("a scheduler is already running")
    session = ClaimedSession(claim, RecordingSessionEvents(journal), RecordingSettler(journal), RecordingRecovery(journal), RecordingReaper(journal))
    with pytest.raises(OrgError):
        session.open("daemon", None, {}, set())
    assert journal == ["take"]


def test_closing_interrupts_the_runs_lets_go_of_the_pidfile_and_announces_the_exit() -> None:
    journal: list[str] = []
    events = RecordingSessionEvents(journal)
    session = ClaimedSession(RecordingClaim(journal), events, RecordingSettler(journal), RecordingRecovery(journal), RecordingReaper(journal))
    session.close("stopped by SIGTERM", {}, 6)
    assert journal == ["terminate", "give up", "exited"] and events.exits == [("stopped by SIGTERM", 6)]


def test_a_signal_is_announced_with_the_run_ids_in_flight_sorted() -> None:
    journal: list[str] = []
    events = RecordingSessionEvents(journal)
    session = ClaimedSession(RecordingClaim(journal), events, RecordingSettler(journal), RecordingRecovery(journal), RecordingReaper(journal))
    table = FakeProcessTable()
    clock = FakeClock()
    runs = {"ops": a_run(table, clock, "ops"), "ceo": a_run(table, clock, "ceo")}
    session.signalled("SIGTERM", "stop", runs)
    assert journal == ["signal"] and events.signals == [("SIGTERM", "stop", sorted(r.run_id for r in runs.values()))]
    assert len(events.signals[0][2]) == 2
