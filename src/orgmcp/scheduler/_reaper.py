"""Reaping runs: the ones that ended, ran out of time or lost their agent - and shutdown, which ends them all."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..kernel import Clock, OrgLayout
from ..mail import BatchStore
from ..settings import OrgSettings
from ..snapshots import OrgSnapshotter
from ._ports import (
    Console, PhaseGuard, RunEvents, RunFailures, RunReaper, RunRecords, RunSettling, RunTerminating, RunWatching, StrayWatch,
)
from ._run import Exit, RunRecord, RunTable


class ExitWatcher(RunWatching):
    def __init__(self, agents: AgentDirectory, settings: OrgSettings, clock: Clock) -> None:
        raise NotImplementedError("red: D-sched-1")

    def watch(self, run: RunRecord) -> Exit | None:
        raise NotImplementedError("red: D-sched-1")


class RunSettlement(RunSettling):
    def __init__(
        self, agents: AgentDirectory, batches: BatchStore, failures: RunFailures, snapshots: OrgSnapshotter, events: RunEvents, console: Console,
        layout: OrgLayout,
    ) -> None:
        raise NotImplementedError("red: D-sched-1")

    def settle(self, run: RunRecord, exit: Exit, elapsed: float) -> None:
        raise NotImplementedError("red: D-sched-1")


class ShutdownTerminator(RunTerminating):
    def __init__(self, batches: BatchStore, events: RunEvents, records: RunRecords) -> None:
        raise NotImplementedError("red: D-sched-1")

    def terminate_all(self, runs: RunTable) -> None:
        raise NotImplementedError("red: D-sched-1")


class PollingRunReaper(RunReaper):
    def __init__(
        self, watching: RunWatching, records: RunRecords, guard: PhaseGuard, strays: StrayWatch, settling: RunSettling, clock: Clock,
        terminating: RunTerminating,
    ) -> None:
        raise NotImplementedError("red: D-sched-1")

    def reap(self, runs: RunTable) -> None:
        raise NotImplementedError("red: D-sched-1")

    def terminate_all(self, runs: RunTable) -> None:
        raise NotImplementedError("red: D-sched-1")
