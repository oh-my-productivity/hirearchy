"""Becoming the scheduler of an organization, and letting go of it."""

from __future__ import annotations

from ..daemon import ExitMarker, SchedulerLock
from ..mail import BatchStore
from ..snapshots import IgnoreList
from ..telemetry import ProcessLabel
from ._ports import Claim, Console, InterruptedRuns, OrphanSettler, RunTerminating, SchedulerSession, SessionEvents
from ._run import RunTable


class ProcessClaim(Claim):
    """This process is the scheduler of the organization while it holds the pidfile."""

    def __init__(self, label: ProcessLabel, lock: SchedulerLock, marker: ExitMarker, ignore: IgnoreList) -> None:
        self._label, self._lock, self._marker, self._ignore = label, lock, marker, ignore

    def take(self) -> None:
        self._label.set("scheduler")
        self._lock.acquire()  # refuses while another live scheduler holds the pidfile
        self._marker.clear()
        self._ignore.ensure_runtime_files()  # the record of runs changes with every run: keep it out of the org's git snapshots

    def give_up(self) -> None:
        self._lock.release()


class BatchRecovery(InterruptedRuns):
    """After a crash, every batch that was inflight goes back to its inbox."""

    def __init__(self, batches: BatchStore, console: Console) -> None:
        self._batches, self._console = batches, console

    def recover(self) -> None:
        for a in self._batches.recover():
            self._console.say(f"recovered interrupted run of {a}")


class ClaimedSession(SchedulerSession):
    """Opening: claim the organization, announce it, settle the orphans of a dead scheduler (before recovering: never redeliver a batch while its previous
    run still lives) and recover. Closing: interrupt the runs in flight, let go of the pidfile, announce the exit."""

    def __init__(self, claim: Claim, events: SessionEvents, settler: OrphanSettler, recovery: InterruptedRuns, runs: RunTerminating) -> None:
        self._claim, self._events, self._settler, self._recovery, self._runs = claim, events, settler, recovery, runs

    def open(self, mode: str, max_runs: int | None, runs: RunTable, blocked: set[str]) -> None:
        self._claim.take()
        self._events.started(mode, max_runs)
        self._settler.settle(runs, blocked)
        self._recovery.recover()

    def close(self, exit_reason: str, runs: RunTable, started: int) -> None:
        self._runs.terminate_all(runs)
        self._claim.give_up()
        self._events.exited(exit_reason, started)

    def signalled(self, name: str, action: str, runs: RunTable) -> None:
        self._events.signalled(name, action, sorted(r.run_id for r in tuple(runs.values())))  # a copy: the handler runs between two bytecodes
