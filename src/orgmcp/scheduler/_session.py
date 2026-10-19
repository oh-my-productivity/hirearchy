"""Becoming the scheduler of an organization, and letting go of it."""

from __future__ import annotations

from ..daemon import ExitMarker, SchedulerLock
from ..mail import BatchStore
from ..snapshots import IgnoreList
from ..telemetry import ProcessLabel
from ._ports import Claim, Console, InterruptedRuns, OrphanSettler, RunTerminating, SchedulerSession, SessionEvents
from ._run import RunTable


class ProcessClaim(Claim):
    def __init__(self, label: ProcessLabel, lock: SchedulerLock, marker: ExitMarker, ignore: IgnoreList) -> None:
        raise NotImplementedError("red: D-sched-2")

    def take(self) -> None:
        raise NotImplementedError("red: D-sched-2")

    def give_up(self) -> None:
        raise NotImplementedError("red: D-sched-2")


class BatchRecovery(InterruptedRuns):
    def __init__(self, batches: BatchStore, console: Console) -> None:
        raise NotImplementedError("red: D-sched-2")

    def recover(self) -> None:
        raise NotImplementedError("red: D-sched-2")


class ClaimedSession(SchedulerSession):
    def __init__(self, claim: Claim, events: SessionEvents, settler: OrphanSettler, recovery: InterruptedRuns, runs: RunTerminating) -> None:
        raise NotImplementedError("red: D-sched-2")

    def open(self, mode: str, max_runs: int | None, runs: RunTable, blocked: set[str]) -> None:
        raise NotImplementedError("red: D-sched-2")

    def close(self, exit_reason: str, runs: RunTable, started: int) -> None:
        raise NotImplementedError("red: D-sched-2")
