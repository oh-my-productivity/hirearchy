"""The runs a dead scheduler left in the registry: killed when they are verifiably ours, redelivered when they are gone or not ours, kept (and the agent
blocked, once said) when in doubt. Never anything else is touched."""

from __future__ import annotations

import signal
from dataclasses import dataclass, field
from pathlib import Path

from orgmcp.kernel.testing import FakeClock, ListEventSink
from orgmcp.processes.testing import FakeProcessTable
from orgmcp.runs import run_id_of
from orgmcp.runs.testing import MemoryRuns
from orgmcp.scheduler._events import SchedulerEvents
from orgmcp.scheduler._orphans import LedgerOrphanSettler, LogRunNotes
from orgmcp.scheduler._run import RunTable
from orgmcp.scheduler.testing import RecordingConsole, RecordingNotes, ScriptedOrphanJudge

from ._support import a_run

LOG = "ceo/runs/20260101T000000000000.log"


@dataclass
class Harness:
    settler: LedgerOrphanSettler
    registry: MemoryRuns
    table: FakeProcessTable
    judge: ScriptedOrphanJudge
    notes: RecordingNotes
    events: ListEventSink
    console: RecordingConsole
    runs: RunTable = field(default_factory=dict)
    blocked: set[str] = field(default_factory=set)

    def settle(self) -> None:
        self.settler.settle(self.runs, self.blocked)

    def record(self, addr: str, pgid: int, log: str = LOG) -> None:
        self.registry.record(addr, {"pgid": pgid, "lstart": "x", "started": 0.0, "scheduler": 1, "log": log})

    def orphan_events(self) -> list[dict[str, object]]:
        return [{"run": e.run, **e.fields} for e in self.events.events if e.kind == "run.orphan"]


def make(verdicts: dict[object, str] | None = None) -> Harness:
    clock = FakeClock()
    registry, table, judge, notes, events, console = MemoryRuns(clock, Path("/org")), FakeProcessTable(clock), ScriptedOrphanJudge(verdicts), RecordingNotes(), ListEventSink(), RecordingConsole()
    return Harness(LedgerOrphanSettler(registry, judge, table, notes, SchedulerEvents(events), console), registry, table, judge, notes, events, console)


def test_a_run_that_is_ours_is_killed_with_its_group_noted_and_forgotten() -> None:
    h = make({5000: "ours"})
    h.table.add(5000)
    leader = h.table.add_member(5000)
    h.record("ceo", 5000)
    h.settle()
    assert not h.table.is_alive(5000) and not h.table.is_alive(leader) and ("group", 5000, signal.SIGKILL) in h.table.signals
    assert h.console.lines == ["ceo: killed the orphaned run of a dead scheduler (process group 5000)"]
    assert h.notes.notes == [({"pgid": 5000, "lstart": "x", "started": 0.0, "scheduler": 1, "log": LOG}, "killed: orphaned run of a scheduler that died")]
    assert h.orphan_events() == [{"run": run_id_of("ceo", LOG), "agent": "ceo", "action": "killed",
                                  "detail": "process group 5000 of a dead scheduler killed; its batch is redelivered"}]
    assert h.registry.all() == {} and h.blocked == set()


def test_a_run_that_is_gone_is_redelivered_without_a_word_to_the_operator() -> None:
    h = make({5000: "gone"})
    h.record("ceo", 5000)
    h.settle()
    assert h.console.lines == [] and h.registry.all() == {} and h.blocked == set()
    assert h.orphan_events() == [{"run": run_id_of("ceo", LOG), "agent": "ceo", "action": "redelivered",
                                  "detail": "the process of a dead scheduler's run is gone; its batch is redelivered"}]


def test_a_process_that_is_not_the_run_is_left_alone_and_the_batch_redelivered() -> None:
    h = make({5000: "foreign"})
    h.table.add(5000)
    h.record("ceo", 5000)
    h.settle()
    assert h.table.is_alive(5000) and h.table.signals == []
    assert h.console.lines == ["ceo: recorded process 5000 is not the run we started; left alone"]
    assert h.orphan_events()[0]["detail"] == "pid 5000 now belongs to another process (left alone); the run's batch is redelivered"
    assert h.registry.all() == {} and h.blocked == set()


def test_a_process_in_doubt_is_kept_its_agent_blocked_and_it_is_said_once() -> None:
    h = make({5000: "doubt"})
    h.table.add(5000)
    h.record("ceo", 5000)
    h.settle()
    h.settle()
    assert h.blocked == {"ceo"} and list(h.registry.all()) == ["ceo"] and h.table.signals == []
    assert h.console.lines == ["ceo: an earlier run (process group 5000) may still be alive and cannot be verified or killed; no new run until it is gone"]
    assert [e["action"] for e in h.orphan_events()] == ["kept"]
    assert h.orphan_events()[0]["detail"] == "process group 5000 may be alive and cannot be verified or killed; no new run until it is gone"


def test_a_blocked_agent_is_free_again_once_its_orphan_is_gone() -> None:
    h = make({5000: "doubt"})
    h.record("ceo", 5000)
    h.settle()
    h.judge.verdicts[5000] = "gone"
    h.settle()
    assert h.blocked == set() and h.registry.all() == {}
    assert [e["action"] for e in h.orphan_events()] == ["kept", "redelivered"]


def test_a_group_that_cannot_be_killed_is_in_doubt_not_ours() -> None:
    h = make({5000: "ours"})
    h.table.add(5000, survives_kill=True)
    h.record("ceo", 5000)
    h.settle()
    assert h.blocked == {"ceo"} and list(h.registry.all()) == ["ceo"]
    assert not any("killed the orphaned run" in line for line in h.console.lines) and h.notes.notes == []
    assert [e["action"] for e in h.orphan_events()] == ["kept"]


def test_an_agent_with_a_run_in_flight_is_not_judged_and_its_record_stays() -> None:
    h = make({5000: "gone"})
    h.record("ceo", 5000)
    clock = FakeClock()
    h.runs["ceo"] = a_run(FakeProcessTable(clock), clock)
    h.settle()
    assert h.judge.asked == [] and list(h.registry.all()) == ["ceo"]


def test_while_an_agent_is_blocked_the_other_records_are_those_of_this_scheduler_and_stay() -> None:
    h = make({5000: "doubt", 5001: "gone"})
    h.record("ceo", 5000)
    h.settle()
    h.record("ops", 5001, "ops/runs/20260101T000001000000.log")  # a run of this scheduler, recorded after it started
    h.settle()
    assert [r["pgid"] for r in h.judge.asked] == [5000, 5000] and sorted(h.registry.all()) == ["ceo", "ops"]


def test_a_record_without_a_log_is_judged_like_any_other() -> None:
    h = make({5000: "gone"})
    h.registry.record("ceo", {"pgid": 5000})
    h.settle()
    assert h.registry.all() == {} and h.orphan_events()[0]["run"] is None


def test_the_note_goes_to_the_log_the_record_names_through_the_log_writer() -> None:
    registry = MemoryRuns(FakeClock(), Path("/org"))
    path = registry.put_log("ceo", "20260101T000000000000.log", "# run of ceo, 1 message(s)\n")
    notes = LogRunNotes(registry)
    notes.note({"log": str(path.relative_to(Path("/org")))}, "killed: orphaned run of a scheduler that died")
    notes.note({"pgid": 1}, "no log recorded: nothing to note")
    assert registry.read_log(path) == b"# run of ceo, 1 message(s)\n\n# killed: orphaned run of a scheduler that died\n"
