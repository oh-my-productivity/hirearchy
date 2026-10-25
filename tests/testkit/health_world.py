"""The world of the tests of ``health``, ``review``, ``progress`` and ``observability`` (E1-c): an ``Org`` whose runtime holds the ports a test chose.

A test that needs the time to stand still (or to move only when it says so), a scheduler that looks a certain way, or an orphan judge that answers
what the story needs, does not replace a module attribute (``core.utcnow``, ``observe.scheduler_state`` ...): it opens the runtime of its organization
again with those ports (``with_ports``, ``wiring.open_runtime(root, overrides)``), and everything the organization does afterwards, the facade as
well as the package under test, reads them.

The functions at the end give the packages' interfaces the call shape the tests have always used (``agent_health(org, addr, now)`` ...): the
assertions of a moved test stay as they were, only the import names this module instead of the former function.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from hirearchy.app import wiring
from hirearchy.app.wire_scheduler import loop_of
from hirearchy.core import ROOT, Org
from hirearchy.health import AgentHealth, OrgHealth
from hirearchy.kernel import Clock
from hirearchy.kernel.testing import FakeClock
from hirearchy.kiro import RunCommand, RunCommandBuilder
from hirearchy.scheduler._ports import Console
from hirearchy.scheduler._run import LoopMemory, LoopState

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
_OVERRIDES = "_port_overrides"  # the overrides the organization was last opened with, kept on it so that a second ``with_ports`` adds to them


class StepClock(FakeClock):
    """A ``FakeClock`` that moves ``step`` per reading (none by default) and jumps to ``T0 + seconds`` with ``at`` (backwards too)."""

    def __init__(self, start: datetime = T0, step: timedelta = timedelta(0)) -> None:
        super().__init__(start)
        self.step = step

    def now(self) -> datetime:
        self.t += self.step
        return self.t

    def at(self, offset_s: float) -> datetime:
        self.t = self.origin + timedelta(seconds=offset_s)
        return self.t


def with_ports(org: Org, overrides: Mapping[type, object]) -> Org:
    """Open the runtime of ``org`` again with ``overrides`` (added to the ones it has): every port is built afresh, over them."""
    merged = {**getattr(org, _OVERRIDES, {}), **overrides}
    org.runtime = wiring.open_runtime(org.root, merged)
    setattr(org, _OVERRIDES, merged)
    return org


def with_clock(org: Org, clock: Clock) -> Org:
    return with_ports(org, {Clock: clock})


def team(path: Path, clock: Clock | None = None, config: Mapping[str, object] | None = None) -> Org:
    """root -> ceo (manager, can hire) -> eng (worker), hired at the time of ``clock`` (the shared ``org`` fixture, with a clock of the test's)."""
    org = Org.init(path / "org", "Test mission", {"poll_seconds": 0.05, **(config or {})})
    if clock is not None:
        with_clock(org, clock)
    org.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    org.hire("ceo", "eng", "Engineer", "Build things.")
    return org


# ------------------------------------------------------------------------------------------ the scheduler


class SecondsClock(Clock):
    """The cadence clock of a scheduler (stall detection, review, heartbeat, grace period) as a function of the test's: waits are the system's."""

    def __init__(self, seconds: Callable[[], float]) -> None:
        self._seconds = seconds

    def now(self) -> datetime:
        return datetime.fromtimestamp(self._seconds(), timezone.utc)

    def time(self) -> float:
        return self._seconds()

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class RunnerCommands(RunCommandBuilder):
    """A runner ``(org, addr, prompt) -> (argv, cwd, env)`` as the command builder of the scheduler."""

    def __init__(self, org: Any, runner: Callable[[Any, str, str], tuple[list[str], Path, dict[str, str]]]) -> None:
        self._org, self._runner = org, runner

    def build(self, addr: str, prompt: str) -> RunCommand:
        argv, cwd, env = self._runner(self._org, addr, prompt)
        return RunCommand(tuple(argv), cwd, dict(env))


class OutputConsole(Console):
    def __init__(self, echo: Callable[[str], None]) -> None:
        self._echo = echo

    def say(self, line: str) -> None:
        self._echo(line)


class Scheduler:
    """The heartbeat loop of ``org.runtime`` (``app.wire_scheduler.loop_of``) with the call shape the tests have always used: ``Scheduler(org, runner,
    echo=..., clock=...)``, ``tick()``, ``acquire()``/``release()``, ``runs``. Without a runner the runs are started with the command of ``kiro``
    (the stub ``kiro-cli`` of the sandbox). ``clock`` is the cadence clock only; runs are timed by the system's."""

    def __init__(
        self, org: Any, runner: Callable[[Any, str, str], tuple[list[str], Path, dict[str, str]]] | None = None,
        echo: Callable[[str], None] = print, clock: Callable[[], float] = time.time, *, ports: Mapping[type, object] | None = None,
    ) -> None:
        self.org = org
        self.state = LoopState()
        commands = RunnerCommands(org, runner) if runner is not None else org.runtime.run_command_builder
        self.loop = loop_of(org.runtime, commands, OutputConsole(echo), SecondsClock(clock), self.state, LoopMemory(), ports)

    @property
    def runs(self) -> dict[str, Any]:
        return self.state.runs

    def reap(self) -> None:
        self.loop.reap()

    def __getattr__(self, name: str) -> Any:
        if name == "loop":
            raise AttributeError(name)
        return getattr(self.loop, name)  # acquire, release, tick, serve, run_once, finished, ...


# ------------------------------------------------------------------------------------------ health


def agent_health(org: Any, addr: str, now: datetime | None = None, limits: Mapping[str, float] | None = None) -> AgentHealth:
    return org.runtime.health_analyzer.agent_health(addr, now, limits)  # type: ignore[no-any-return]


def org_health(org: Any, root: str = ROOT, now: datetime | None = None) -> OrgHealth:
    return org.runtime.health_analyzer.org_health(root, now)  # type: ignore[no-any-return]


def thresholds(org: Any) -> dict[str, float]:
    return org.runtime.health_thresholds.thresholds()  # type: ignore[no-any-return]


def render_text(health: OrgHealth, *, causes: bool = False) -> str:
    """The report as text (the renderer is a pure function of its argument: any runtime has it)."""
    return wiring.open_runtime(Path.cwd()).health_renderer.render_text(health, causes=causes)  # type: ignore[no-any-return]
