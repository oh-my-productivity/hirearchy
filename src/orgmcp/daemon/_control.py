"""Start and stop, as one port."""

from __future__ import annotations

from ._ports import SchedulerLauncher, SchedulerStopper
from .api import SchedulerControl


class DetachedSchedulerControl(SchedulerControl):
    def __init__(self, launcher: SchedulerLauncher, stopper: SchedulerStopper) -> None:
        self._launcher = launcher
        self._stopper = stopper

    def start(self, max_runs: int | None = None, until_done: bool = False) -> int:
        raise NotImplementedError

    def stop(self, wait: float = 15.0) -> str:
        raise NotImplementedError
