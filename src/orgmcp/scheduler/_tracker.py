"""The registry of runs in flight (``.runtime/running.json``)."""

from __future__ import annotations

from ..kernel import OrgLayout
from ..processes import ProcessInspector
from ..runs import RunRegistry, run_record
from ._ports import RunRecords
from ._run import RunRecord


class RunTracker(RunRecords):
    """Records each run as {pgid, lstart, started, scheduler, log}: what a new scheduler needs to judge the run of a dead one."""

    def __init__(self, registry: RunRegistry, processes: ProcessInspector, layout: OrgLayout) -> None:
        self._registry, self._processes, self._layout = registry, processes, layout

    def record(self, addr: str, run: RunRecord) -> None:
        self._registry.record(addr, run_record(
            pgid=run.proc.pid,  # started in its own session, so pgid == pid
            lstart=self._processes.start_time(run.proc.pid),
            started=run.started,
            scheduler=self._processes.own_ids()[0],
            log=str(run.log.relative_to(self._layout.root)),
        ))

    def forget(self, *addrs: str) -> None:
        self._registry.forget(*addrs)
