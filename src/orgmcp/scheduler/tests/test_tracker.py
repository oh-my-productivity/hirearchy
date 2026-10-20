"""The registry of runs in flight: what a new scheduler needs to judge the run of a dead one."""

from __future__ import annotations

from orgmcp.kernel import OrgPaths
from orgmcp.kernel.testing import FakeClock
from orgmcp.processes.testing import FakeProcessTable
from orgmcp.runs.testing import MemoryRuns
from orgmcp.scheduler._tracker import RunTracker

from ._support import ROOT_DIR, a_run


def make() -> tuple[RunTracker, MemoryRuns, FakeProcessTable, FakeClock]:
    clock = FakeClock()
    runs, table = MemoryRuns(clock, ROOT_DIR), FakeProcessTable(clock, own_pid=4321)
    return RunTracker(runs, table, OrgPaths(ROOT_DIR)), runs, table, clock


def test_a_run_is_recorded_with_its_group_its_start_time_the_scheduler_and_its_log() -> None:
    tracker, runs, table, clock = make()
    run = a_run(table, clock)
    tracker.record("ceo", run)
    assert runs.all() == {"ceo": {"pgid": run.proc.pid, "lstart": table.start_time(run.proc.pid), "started": run.started, "scheduler": 4321,
                                  "log": "ceo/runs/20260101T000000000000.log"}}


def test_forget_takes_out_the_record_of_the_first_agent_that_has_one() -> None:
    tracker, runs, table, clock = make()
    tracker.record("ceo", a_run(table, clock))
    tracker.record("ceo/eng", a_run(table, clock, "ceo/eng"))
    tracker.forget("ceo")
    assert list(runs.all()) == ["ceo/eng"]
    tracker.forget("nobody", "ceo/eng")
    assert runs.all() == {}
