"""The run lifecycle of the scheduler over the ports of a real runtime: ``wire_scheduler.lifecycle_of``, and the loop that holds it.

The two clocks (ARCHITECTURE.md 1.3 decision 6, risk 11): the clock given to the loop (``Scheduler(clock=...)`` of the test world) is the cadence of the stall ladder, the review and
the heartbeat; a run is timed by the run clock, which is the system's. Its output goes through the descriptor of the run log's sink (``fileno``)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from hirearchy.app import Org, wire_scheduler, wiring
from hirearchy.processes import ProcessInspector, ProcessSpawner
from hirearchy.processes.testing import FakeProcessTable
from hirearchy.scheduler._run import RunCount, RunTable
from hirearchy.scheduler.testing import CapturingSpawner, CatchingGuard, RecordingConsole, ScriptedCommands
from testkit.health_world import Scheduler
from testkit.kiro_world import Runner


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission", {"poll_seconds": 0.05, "run_timeout": 2, "max_failures": 1})
    made.hire("root", "ceo", "Chief", "Run it.")
    made.delegate("root", "ceo", "T", "g", "a", budget=3)
    return made


def script(code: str) -> Runner:
    def build(o: Org, addr: str, prompt: str) -> tuple[list[str], Path, dict[str, str]]:
        return [sys.executable, "-c", code], o.dir(addr), {"PATH": "/usr/bin:/bin"}

    return build


def until_done(sched: Scheduler, limit: float = 20.0) -> None:
    deadline = time.time() + limit
    while sched.runs and time.time() < deadline:
        sched.reap()
        time.sleep(0.02)
    assert not sched.runs


def test_the_lifecycle_runs_a_run_over_the_ports_of_a_runtime(org: Org) -> None:
    table = FakeProcessTable()
    org.runtime = wiring.open_runtime(org.root, {ProcessSpawner: CapturingSpawner(table), ProcessInspector: table})
    console, commands = RecordingConsole(), ScriptedCommands(("kiro-cli", "chat"), org.root, {"PATH": "/bin"})
    life = wire_scheduler.lifecycle_of(org.runtime, commands, console, CatchingGuard(), RunCount())
    runs: RunTable = {}
    assert life.starter.launch(runs, set(), None) == 1
    run = runs["ceo"]
    assert org.ledger("running")["ceo"]["pgid"] == run.proc.pid and len(org.messages("ceo", "inflight")) == 1
    assert console.lines == ["ceo: started run (1 message(s))"]
    table.exit(run.proc.pid, 0)
    life.reaper.reap(runs)
    assert runs == {} and org.ledger("running") == {} and org.messages("ceo", "inflight") == []
    assert console.lines[-1].startswith("ceo: run finished in ")


def test_a_run_is_timed_by_the_run_clock_not_by_the_clock_of_the_cadence(org: Org) -> None:
    lines: list[str] = []
    sched = Scheduler(org, script("import time; time.sleep(30)"), echo=lines.append, clock=lambda: 4_000_000_000.0)  # the cadence is far in the future
    sched.acquire()
    try:
        sched.tick()
        run = sched.runs["ceo"]
        sched.tick()
        sched.tick()
        assert "ceo" in sched.runs and run.proc.poll() is None and run.timed_out is False  # the cadence clock does not time out a run
        assert run.started < 4_000_000_000.0
    finally:
        sched.release()


def test_a_run_past_its_timeout_is_killed_whatever_the_cadence_clock_says(org: Org) -> None:
    lines: list[str] = []
    sched = Scheduler(org, script("import time; time.sleep(30)"), echo=lines.append, clock=lambda: 0.0)  # the cadence stands still
    sched.acquire()
    try:
        sched.tick()
        run = sched.runs["ceo"]
        run.started -= 10  # it has been running for ten seconds by the run clock; the timeout is two
        sched.reap()
        assert sched.runs == {} and run.timed_out and run.killed
        assert "# killed after 2s timeout" in run.log.read_text(encoding="utf-8")
    finally:
        sched.release()


def test_the_output_of_a_run_lands_in_its_log_through_the_descriptor_of_the_sink(org: Org) -> None:
    sched = Scheduler(org, script("print('hello from the agent'); import sys; print('and stderr', file=sys.stderr)"), echo=lambda _: None)
    sched.tick()
    log = sched.runs["ceo"].log
    until_done(sched)
    text = log.read_text(encoding="utf-8")
    output = text.split("# ---- output ----\n", 1)[1]
    assert "hello from the agent\n" in output and "and stderr\n" in output and text.rstrip().endswith("# exit 0 after 0s")


def test_the_total_of_runs_started_is_the_count_of_the_lifecycle(org: Org) -> None:
    sched = Scheduler(org, script("pass"), echo=lambda _: None)
    assert sched.state.count.total == 0
    sched.tick(max_runs=1)
    assert sched.state.count.total == 1
    until_done(sched)
    sched.state.count.total = 5
    assert sched.state.count.total == 5
