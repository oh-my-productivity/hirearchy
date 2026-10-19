"""The registry of runs in flight (``.runtime/running.json``)."""

from __future__ import annotations

from ..kernel import OrgLayout
from ..processes import ProcessInspector
from ..runs import RunRegistry
from ._ports import RunRecords
from ._run import RunRecord


class RunTracker(RunRecords):
    """Records each run as {pgid, lstart, started, scheduler, log}: what a new scheduler needs to judge the run of a dead one."""

    def __init__(self, registry: RunRegistry, processes: ProcessInspector, layout: OrgLayout) -> None:
        raise NotImplementedError("red: D-sched-1")

    def record(self, addr: str, run: RunRecord) -> None:
        raise NotImplementedError("red: D-sched-1")

    def forget(self, *addrs: str) -> None:
        raise NotImplementedError("red: D-sched-1")
