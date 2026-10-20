"""The scheduler's loop over a real ``Org`` for the tests that run agents as real (fake-agent) processes.

``loop_over`` makes the ``HeartbeatLoop`` of ``org.runtime`` the way the composition root does (``app.wire_scheduler.loop_of``): the runner of a test is a
``(org, addr, prompt) -> (argv, cwd, env)`` function, the output is a function of one line, and the cadence clock (stall detection, review, heartbeat, grace
period) is a function that returns seconds, so that a test can move time forward without sleeping. Runs are timed by the system's clock, as always.
What a test asks of the loop it asks of the loop's own collaborators: ``loop.state`` (``runs``, ``blocked``, ``count``, ``mode``), ``loop.reap()``, ``loop.start(addr)``,
``org.runtime.runnable_query``, ``org.runtime.open_work``. ``GraceWaiting`` is the grace period of an until-done scheduler over the ports of a runtime and a loop.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from orgmcp.app import wire_kiro
from orgmcp.app.wire_scheduler import loop_of
from orgmcp.kernel import Clock
from orgmcp.kiro import RunCommand, RunCommandBuilder
from orgmcp.scheduler._exit import GraceWait
from orgmcp.scheduler._loop import HeartbeatLoop
from orgmcp.scheduler._ports import Console
from orgmcp.scheduler._run import GraceMemory, LoopMemory, LoopState, Standing
from orgmcp.scheduler._work import QueriedWork

Runner = Callable[[Any, str, str], tuple[list[str], Any, dict[str, str]]]


class RunnerCommands(RunCommandBuilder):
    """A test's runner ``(org, addr, prompt)`` as the command builder of the run lifecycle."""

    def __init__(self, org: Any, runner: Runner) -> None:
        self._org, self._runner = org, runner

    def build(self, addr: str, prompt: str) -> RunCommand:
        argv, cwd, env = self._runner(self._org, addr, prompt)
        return RunCommand(tuple(argv), cwd, env)


class EchoConsole(Console):
    """What the scheduler says goes to a function of one line."""

    def __init__(self, echo: Callable[[str], None]) -> None:
        self._echo = echo

    def say(self, line: str) -> None:
        self._echo(line)


class SecondsClock(Clock):
    """A cadence clock whose time is a function that returns seconds; the waits are the system's."""

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


def loop_over(
    org: Any, runner: Runner | None = None, echo: Callable[[str], None] = print, clock: Callable[[], float] = time.time, *,
    overrides: Mapping[type, object] | None = None, state: LoopState | None = None, memory: LoopMemory | None = None,
) -> HeartbeatLoop:
    """The loop of ``org.runtime`` as it is when this is called. ``overrides`` put other objects in the place of ports of the runtime (a failing ``StallLadder``,
    a ``HealthReviewer``, a ``StrayProbe``, a ``ProcessSignaller``); ``state`` and ``memory`` hand a loop what an earlier one owned and remembered."""
    runtime = org.runtime
    commands = RunnerCommands(org, runner) if runner else wire_kiro.run_command_builder(runtime, "kiro-cli", runtime.profile_provisioner)
    return loop_of(runtime, commands, EchoConsole(echo), SecondsClock(clock), state or LoopState(), memory, overrides)


def runnable_of(org: Any, loop: HeartbeatLoop) -> list[str]:
    """The agents that could start a run now, not counting the ones the loop has in flight or blocked."""
    return org.runtime.runnable_query.runnable(exclude=set(loop.state.runs) | loop.state.blocked)


class GraceWaiting:
    """The grace period of an until-done scheduler: ``waiting()`` is the exit reason once nothing has progressed without the user for
    ``until_done_grace_seconds``, else ''; ``waiting.since`` is when the count began. It looks at the runs and the blocked agents of ``loop`` and at the
    cadence clock ``clock`` (a function that returns seconds), over the ports of the runtime of ``org``; what it says goes to ``echo``."""

    def __init__(self, org: Any, loop: HeartbeatLoop, echo: Callable[[str], None], clock: Callable[[], float]) -> None:
        runtime = org.runtime
        self.loop, self.memory = loop, GraceMemory()
        work = QueriedWork(runtime.open_work, runtime.runnable_query, runtime.waiting_on_user)
        self.grace = GraceWait(work, runtime.settings, SecondsClock(clock), EchoConsole(echo), self.memory)

    @property
    def since(self) -> float | None:
        return self.memory.since

    def __call__(self, max_runs: int | None = None) -> str:
        s = self.loop.state
        return self.grace.check(Standing(s.runs, s.blocked, max_runs is None or s.count.total < max_runs))


def scheduler_line(org: Any) -> str:
    """The status line of the scheduler of ``org`` (``scheduler: stopped (...)``)."""
    return org.runtime.scheduler_status.describe()


def waiting_for_user(org: Any) -> Any:
    """Is every open root task unable to progress without the user, as a scheduler with no runs of its own sees it? (None if not)"""
    return org.runtime.waiting_on_user.analyze()


def nothing_left(org: Any) -> bool:
    """Would an until-done scheduler with no runs of its own exit at once?"""
    return org.runtime.open_work.nothing_to_do()
