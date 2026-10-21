"""``wire_scheduler.loop_of``: the loop over the ports of a real runtime, the ports a test puts in place of the runtime's, and the loop made again over
another runtime going on where the old one was."""

from __future__ import annotations

import dataclasses
import sys
import time
from pathlib import Path

import pytest

from hirearchy.app import Org, wire_scheduler, wiring
from hirearchy.attention import HumanQueue
from hirearchy.attention.testing import ListHumanQueue
from hirearchy.processes import ProcessInspector, ProcessSpawner
from hirearchy.processes.testing import FakeProcessTable
from hirearchy.scheduler import SchedulerLoop
from hirearchy.scheduler._loop import HeartbeatLoop
from hirearchy.scheduler._phases import GuardedPhase
from hirearchy.scheduler._run import LoopMemory, LoopState
from hirearchy.scheduler.testing import CapturingSpawner, RecordingConsole, ScriptedCommands, ScriptedLadder
from testkit.health_world import SecondsClock
from hirearchy.stalls import StallLadder
from hirearchy.templates.testing import RecordingNotices


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission", {"poll_seconds": 0.05, "run_timeout": 2, "max_failures": 1})
    made.hire("root", "ceo", "Chief", "Run it.")
    made.delegate("root", "ceo", "T", "g", "a", budget=3)
    return made


def make(org: Org, state: LoopState | None = None, memory: LoopMemory | None = None, overrides: dict[type, object] | None = None,
         console: RecordingConsole | None = None, cadence: float | None = None) -> HeartbeatLoop:
    commands = ScriptedCommands((sys.executable, "-c", "pass"), org.root, {"PATH": "/usr/bin:/bin"})
    clock = SecondsClock(lambda: cadence if cadence is not None else time.time())
    return wire_scheduler.loop_of(org.runtime, commands, console or RecordingConsole(), clock, state or LoopState(), memory, overrides)


def test_the_loop_is_a_scheduler_loop_over_the_ports_of_the_runtime(org: Org) -> None:
    loop = make(org)
    assert isinstance(loop, SchedulerLoop)
    names = [p.name if isinstance(p, GuardedPhase) else type(p).__name__ for p in loop.phases]
    assert names == ["FailureLedgerRepair", "ReapPhase", "orphan check", "FundedResume", "RunLaunch", "stall check", "health review", "event log upkeep"]


def test_a_pass_starts_the_run_of_an_agent_with_mail_and_the_run_is_in_the_state_the_loop_owns(org: Org) -> None:
    table = FakeProcessTable()
    org.runtime = wiring.open_runtime(org.root, {ProcessSpawner: CapturingSpawner(table), ProcessInspector: table})
    state = LoopState()
    loop = make(org, state)
    assert loop.tick() is True
    assert list(state.runs) == ["ceo"] and state.count.total == 1 and loop.state is state
    assert org.ledger("running")["ceo"]["pgid"] == state.runs["ceo"].proc.pid


def test_a_port_put_in_place_of_the_runtimes_is_the_one_the_loop_uses(org: Org) -> None:
    ladder, queue = ScriptedLadder("ceo: reminded about open task x"), ListHumanQueue([("m1", "Needs you: a")])
    console = RecordingConsole()
    loop = make(org, console=console, overrides={StallLadder: ladder, HumanQueue: queue})
    loop.tick()
    assert ladder.checks == 1 and "ceo: reminded about open task x" in console.lines


def test_the_stall_ladder_is_timed_by_the_cadence_clock(org: Org) -> None:
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    notices = RecordingNotices()
    org.runtime = dataclasses.replace(org.runtime, notices=notices)
    console = RecordingConsole()
    make(org, console=console, cadence=4_000_000_000.0).tick()  # the cadence is far in the future, the clock of the runtime is not
    assert [call[0] for call in notices.calls] == ["nudge"] and console.lines[0].startswith("ceo: reminded about open task ")


def test_a_loop_made_again_over_another_runtime_goes_on_where_the_old_one_was(org: Org) -> None:
    ladder = ScriptedLadder()
    ladder.fail = RuntimeError("kaput")
    state, memory, console = LoopState(), LoopMemory(), RecordingConsole()
    make(org, state, memory, {StallLadder: ladder}, console).tick()
    org.runtime = wiring.open_runtime(org.root)  # another runtime
    state.blocked.add("ops")
    again = make(org, state, memory, {StallLadder: ladder}, console)
    again.tick()
    assert len([line for line in console.lines if "kaput" in line]) == 1  # said once: the guard remembers what it said
    assert again.state is state and state.blocked == set()  # ops had no record of an orphan: the check of the new loop freed it
