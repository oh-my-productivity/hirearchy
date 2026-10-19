"""``DetachedSchedulerControl``: start and stop are the launcher's and the stopper's, with the defaults of the port."""

from __future__ import annotations

import pytest

from orgmcp.daemon._control import DetachedSchedulerControl
from orgmcp.daemon._ports import SchedulerLauncher, SchedulerStopper

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-daemon")


class Launcher(SchedulerLauncher):
    def __init__(self) -> None:
        self.starts: list[tuple[int | None, bool]] = []

    def start(self, max_runs: int | None, until_done: bool) -> int:
        self.starts.append((max_runs, until_done))
        return 4242


class Stopper(SchedulerStopper):
    def __init__(self) -> None:
        self.stops: list[float] = []

    def stop(self, wait: float) -> str:
        self.stops.append(wait)
        return "scheduler stopped (pid 4242)"


def test_start_is_the_launchers_and_returns_its_pid() -> None:
    launcher = Launcher()
    control = DetachedSchedulerControl(launcher, Stopper())
    assert control.start(3, True) == 4242
    assert launcher.starts == [(3, True)]


def test_start_without_arguments_has_no_cap_and_does_not_end_by_itself() -> None:
    launcher = Launcher()
    DetachedSchedulerControl(launcher, Stopper()).start()
    assert launcher.starts == [(None, False)]


def test_stop_is_the_stoppers_and_waits_fifteen_seconds_by_default() -> None:
    stopper = Stopper()
    control = DetachedSchedulerControl(Launcher(), stopper)
    assert control.stop() == "scheduler stopped (pid 4242)"
    control.stop(2.5)
    assert stopper.stops == [15.0, 2.5]
