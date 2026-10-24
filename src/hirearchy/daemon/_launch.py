"""Starting a detached scheduler."""

from __future__ import annotations

from ..kernel import OrgError
from ..processes import ProcessSpawner
from ._ports import LaunchEnvironment, LaunchSite, SchedulerLauncher, StartupWatch
from ._refusals import check_startable
from .api import SchedulerCommand, SchedulerStatus


class DetachedLauncher(SchedulerLauncher):
    def __init__(
        self,
        status: SchedulerStatus,
        site: LaunchSite,
        environment: LaunchEnvironment,
        command: SchedulerCommand,
        spawner: ProcessSpawner,
        watch: StartupWatch,
    ) -> None:
        self._status = status
        self._site = site
        self._environment = environment
        self._command = command
        self._spawner = spawner
        self._watch = watch

    def start(self, max_runs: int | None, until_done: bool) -> int:
        if max_runs is not None and max_runs < 0:
            raise OrgError("max_runs must be 0 or more")
        check_startable(self._status.state())
        log = self._site.prepare()
        env = self._environment.variables()
        argv = self._command.argv(max_runs, until_done)
        self._site.announce(log, argv)
        pid = self._spawner.spawn_detached(argv, cwd=self._site.directory(), env=env, log=log)
        return self._watch.await_start(pid, log)
