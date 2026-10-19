"""Starting a detached scheduler."""

from __future__ import annotations

from ..processes import ProcessSpawner
from ._ports import Children, LaunchEnvironment, LaunchSite, SchedulerLauncher, StartupWatch
from .api import SchedulerCommand, SchedulerStatus


class DetachedLauncher(SchedulerLauncher):
    def __init__(
        self,
        status: SchedulerStatus,
        site: LaunchSite,
        environment: LaunchEnvironment,
        command: SchedulerCommand,
        spawner: ProcessSpawner,
        children: Children,
        watch: StartupWatch,
    ) -> None:
        self._status = status
        self._site = site
        self._environment = environment
        self._command = command
        self._spawner = spawner
        self._children = children
        self._watch = watch

    def start(self, max_runs: int | None, until_done: bool) -> int:
        raise NotImplementedError
