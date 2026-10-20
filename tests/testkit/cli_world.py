"""The world of the command-line tests: the clock of every organization the command line opens, and the clock its commands wait by.

The command line opens its own runtime for ``--root``, so a test cannot hand that runtime a clock; ``clock_is`` gives the ``Clock`` to the process
overrides of the composition root (the way ``testkit.scheduler.scheduler_is`` does for the scheduler's status): every organization opened
afterwards - the one the test builds, the one the command line opens - reads that clock. ``cli_clocked`` is the command line whose commands
sleep and time by a given clock (``obs now --watch``, ``obs events --follow``); ``SleepingClock`` is a ``FakeClock`` whose ``sleep`` is the test's.
``main`` is ``orgmcp.main``, the console entry (re-exported here: the package ``orgmcp`` loads the facade, which a test inside ``orgmcp.cli`` may not
import).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime

from orgmcp import main
from orgmcp.app.wire_cli import run_cli
from orgmcp.kernel import Clock
from orgmcp.kernel.testing import T0, FakeClock

__all__ = ["SleepingClock", "cli_clocked", "clock_is", "main"]


def clock_is(process_overrides: Callable[[Mapping[type, object]], object], clock: Clock) -> Clock:
    """Every organization opened until the end of the test (by the test, by the command line) reads ``clock`` (``process_overrides``: the fixture)."""
    process_overrides({Clock: clock})
    return clock


class SleepingClock(FakeClock):
    """A ``FakeClock`` whose ``sleep`` calls ``sleeper`` (which may raise ``KeyboardInterrupt``, the way Ctrl-C ends a watch)."""

    def __init__(self, sleeper: Callable[[float], None], start: datetime = T0) -> None:
        super().__init__(start)
        self._sleeper = sleeper

    def sleep(self, seconds: float) -> None:
        self._sleeper(seconds)


def cli_clocked(clock: Clock) -> Callable[[Sequence[str]], None]:
    """``orgmcp.main`` whose commands wait and time by ``clock``."""

    def main(argv: Sequence[str]) -> None:
        run_cli(argv, clock)

    return main
