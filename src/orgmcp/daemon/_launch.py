"""Starting a detached scheduler."""

from __future__ import annotations

from ..kernel import OrgError
from ..processes import ProcessSpawner
from ._ports import Children, LaunchEnvironment, LaunchSite, SchedulerLauncher, StartupWatch
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
        if max_runs is not None and max_runs < 0:
            raise OrgError("max_runs must be 0 or more")
        check_startable(self._status.state())
        log = self._site.prepare()
        env = self._environment.variables()
        argv = self._command.argv(max_runs, until_done)
        self._site.announce(log, argv)
        handle = self._spawner.spawn_detached(argv, cwd=self._site.directory(), env=env, log=log)
        self._children.adopt(handle)
        self._watch.await_start(handle, log)
        return handle.pid
