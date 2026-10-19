"""Which agents get a run in a pass: the cap on parallel runs, the cap on runs started, the ones already running or blocked, the admission."""

from __future__ import annotations

from pathlib import Path

from orgmcp.processes.testing import FakeProcessTable
from orgmcp.access.testing import StaticAccess
from orgmcp.scheduler._run import RunCount, RunRecord
from orgmcp.scheduler._starter import AgentRunLauncher
from orgmcp.scheduler.testing import RecordingInitiation, ScriptedAdmission

from ._support import red

pytestmark = red

AGENTS = ["a", "b", "c", "d"]


def launcher(allowed: list[str], parallel: int = 8, count: RunCount | None = None) -> tuple[AgentRunLauncher, ScriptedAdmission, RecordingInitiation, RunCount]:
    access = StaticAccess(Path("/memory/org"), f"---\nmax_parallel: {parallel}\n---\n# Organization\n")
    for addr in AGENTS:
        access.put_agent(addr, {})
    count = count or RunCount()
    table = FakeProcessTable()
    admission, initiation = ScriptedAdmission(allowed), RecordingInitiation(count, lambda: table.spawn(["x"], cwd=Path("/"), env={}, stdin=None, stdout=None))
    return AgentRunLauncher(access.agents, access.settings, admission, initiation, count), admission, initiation, count


def test_every_admitted_agent_gets_a_run_in_order() -> None:
    starter, admission, initiation, count = launcher(["a", "c"])
    runs: dict[str, RunRecord] = {}
    assert starter.launch(runs, set(), None) == 2
    assert initiation.started == ["a", "c"] and list(runs) == ["a", "c"] and count.total == 2 and admission.asked == AGENTS


def test_running_and_blocked_agents_are_not_asked_at_all() -> None:
    starter, admission, initiation, _ = launcher(AGENTS)
    runs: dict[str, RunRecord] = {}
    starter.start(runs, "a")
    assert starter.launch(runs, {"b"}, None) == 2
    assert initiation.started == ["a", "c", "d"] and admission.asked == ["c", "d"]


def test_max_parallel_caps_the_runs_in_flight() -> None:
    starter, _, initiation, _ = launcher(AGENTS, parallel=2)
    runs: dict[str, RunRecord] = {}
    assert starter.launch(runs, set(), None) == 2 and initiation.started == ["a", "b"]
    assert starter.launch(runs, set(), None) == 0


def test_max_runs_caps_the_runs_this_scheduler_started_in_all() -> None:
    starter, _, initiation, count = launcher(AGENTS, count=RunCount(2))
    runs: dict[str, RunRecord] = {}
    assert starter.launch(runs, set(), 3) == 1 and initiation.started == ["a"] and count.total == 3
    assert starter.launch(runs, set(), 3) == 0
    assert starter.launch(runs, set(), 0) == 0


def test_start_starts_one_run_without_asking() -> None:
    starter, admission, initiation, _ = launcher([])
    starter.start({}, "b")
    assert initiation.started == ["b"] and admission.asked == []
