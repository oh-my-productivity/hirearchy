"""Start and stop, as one port."""

from __future__ import annotations

from ._ports import SchedulerLauncher, SchedulerStopper
from .api import SchedulerControl


class DetachedSchedulerControl(SchedulerControl):
    def __init__(self, launcher: SchedulerLauncher, stopper: SchedulerStopper) -> None:
        self._launcher = launcher
        self._stopper = stopper

    def start(self, max_runs: int | None = None, until_done: bool = False) -> int:
        return self._launcher.start(max_runs, until_done)

    def stop(self, wait: float = 15.0) -> str:
        return self._stopper.stop(wait)
