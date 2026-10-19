"""(f) The scheduler's pid file matches a live scheduler."""

from __future__ import annotations

from collections.abc import Sequence

from ...daemon import SchedulerStatus
from ...kernel import JsonObject
from ...mail import MessageFile
from .._ports import IntegrityCheck, SchedulerPidFile
from ._base import verdict


class PidfileSane(IntegrityCheck):
    """When there is a pid file, the scheduler status says its process is this organization's scheduler."""

    def __init__(self, pidfile: SchedulerPidFile, scheduler: SchedulerStatus) -> None:
        self._pidfile, self._scheduler = pidfile, scheduler

    def run(self, files: Sequence[MessageFile], now: float) -> JsonObject:
        name = "scheduler pid file matches a live scheduler"
        if not self._pidfile.exists():
            return verdict("f", name, [], "no pid file: no scheduler claims to run")
        st = self._scheduler.state()
        if st.state == "running":
            return verdict("f", name, [], f"pid {st.pid} is this organization's scheduler")
        if st.state == "unverified":
            return verdict("f", name, [f".runtime/scheduler.pid names pid {st.pid}, alive but not verified as this org's scheduler ({st.detail})"])
        return verdict("f", name, [".runtime/scheduler.pid is stale: its process is gone (a scheduler start replaces it; remove it if none will start)"])
