"""The scheduler loop over an organization, for the tests of the mailbox that need a pass of the scheduler (does a held note start a run?).

A test of ``mail`` may not import the scheduler (import contracts), so it takes the loop from here: made by the composition root over the ports of
``org.runtime`` (``app.wire_scheduler.loop_of``), with the command of a run given by a ``runner(org, addr, prompt) -> (argv, cwd, env)`` and its output
dropped. The loop is the one the command line serves; ``tick`` is one pass.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from orgmcp.app import wire_scheduler
from orgmcp.kernel._system import SystemClock
from orgmcp.kiro import RunCommand, RunCommandBuilder
from orgmcp.scheduler._loop import HeartbeatLoop
from orgmcp.scheduler._run import LoopState
from orgmcp.scheduler.testing import RecordingConsole

Runner = Callable[[Any, str, str], tuple[Sequence[str], Path, Mapping[str, str]]]


class RunnerCommands(RunCommandBuilder):
    """The command of a run is what ``runner(org, addr, prompt)`` says."""

    def __init__(self, org: Any, runner: Runner) -> None:
        self._org, self._runner = org, runner

    def build(self, addr: str, prompt: str) -> RunCommand:
        argv, cwd, env = self._runner(self._org, addr, prompt)
        return RunCommand(tuple(argv), cwd, env)


def scheduler_over(org: Any, runner: Runner) -> HeartbeatLoop:
    """The loop over ``org.runtime`` (as it is now: make it again after replacing the runtime), runs started with ``runner``, output dropped."""
    return wire_scheduler.loop_of(org.runtime, RunnerCommands(org, runner), RecordingConsole(), SystemClock(), LoopState())
