"""Reaping runs: the ones that ended, ran out of time or lost their agent - and shutdown, which ends them all."""

from __future__ import annotations

import signal
import subprocess

from ..agents import AgentDirectory
from ..kernel import Clock, OrgLayout
from ..kiro import THROTTLE_EXIT
from ..mail import BatchStore
from ..runs import log_exit, log_interrupted, log_retired, log_timeout
from ..settings import OrgSettings
from ..snapshots import OrgSnapshotter
from ._ports import (
    Console,
    PhaseGuard,
    RunEvents,
    RunFailures,
    RunReaper,
    RunRecords,
    RunSettling,
    RunTerminating,
    RunWatching,
    StrayWatch,
    ThrottleCredits,
)
from ._run import Exit, RunRecord, RunTable


class ExitWatcher(RunWatching):
    """A run ends by itself, or is ended here: past ``run_timeout`` (by the clock it is given: the run clock) or when its agent was retired."""

    def __init__(self, agents: AgentDirectory, settings: OrgSettings, clock: Clock) -> None:
        self._agents, self._settings, self._clock = agents, settings, clock

    def watch(self, run: RunRecord) -> Exit | None:
        timeout = self._settings.number("run_timeout")
        code = run.proc.poll()
        why = None
        if code is None and self._clock.time() - run.started > timeout:
            run.proc.signal_group(signal.SIGKILL)
            code = run.proc.wait()
            run.logf.write(log_timeout(timeout))
            run.killed = run.timed_out = True
            why = f"timed out: killed after {timeout:.0f}s"
        elif code is None and not self._agents.exists(run.addr):  # retired mid-run: nobody will read its output
            run.proc.signal_group(signal.SIGKILL)
            code = run.proc.wait()
            run.logf.write(log_retired())
            run.killed = True
            why = "killed: the agent was retired during its run"
        return None if code is None else Exit(code, why)


class RunSettlement(RunSettling):
    def __init__(
        self, agents: AgentDirectory, batches: BatchStore, failures: RunFailures, snapshots: OrgSnapshotter, events: RunEvents, console: Console,
        layout: OrgLayout, throttles: ThrottleCredits,
    ) -> None:
        self._agents, self._batches, self._failures, self._snapshots = agents, batches, failures, snapshots
        self._events, self._console, self._layout, self._throttles = events, console, layout, throttles

    def settle(self, run: RunRecord, exit: Exit, elapsed: float) -> None:
        addr, code, ok = run.addr, exit.code, exit.code == 0
        if not self._agents.exists(addr):  # retired while the run was in flight: nothing left to settle
            self._events.ended(run, code, exit.why or ("agent retired during its run" if not ok else None))
            self._console.say(f"{addr}: was retired during its run (exit {code}); nothing to settle")
            self._snapshots.commit(f"{addr}: run ended after retirement (exit {code})")
            return
        self._batches.end(addr, ok)
        self._events.ended(run, code, exit.why)
        if ok:
            self._failures.cleared(addr)
            self._console.say(f"{addr}: run finished in {elapsed:.0f}s")
        else:
            self._failed(run, exit)
        rel = run.log.relative_to(self._layout.root)
        self._snapshots.commit(f"{addr}: run {'ok' if ok else f'failed ({code})'}, {run.batch} message(s) [{rel}]")


    def _failed(self, run: RunRecord, exit: Exit) -> None:
        """A failed run: charged and counted, unless the launcher said it was throttled before any tool effect (exit 75 of a run that was not killed)
        and the runtime credited it; a free credit is no failure (the batch is back in the inbox and the run is retried)."""
        kind = self._throttles.credit(run) if exit.code == THROTTLE_EXIT and not run.killed else ""
        if kind:
            self._console.say(f"{run.addr}: run throttled by the model service before any tool effect: not charged" + (", retried" if kind == "free" else ""))
        if kind != "free":
            self._failures.failed(run.addr, run.log, run.traces)


class ShutdownTerminator(RunTerminating):
    """SIGTERM to every group, ten seconds of grace each, then SIGKILL to the group (which also reaps tool subprocesses that ignored SIGTERM)."""

    def __init__(self, batches: BatchStore, events: RunEvents, records: RunRecords) -> None:
        self._batches, self._events, self._records = batches, events, records

    def terminate_all(self, runs: RunTable) -> None:
        for run in list(runs.values()):
            run.proc.signal_group(signal.SIGTERM)
        for addr, run in list(runs.items()):
            try:
                run.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            run.proc.signal_group(signal.SIGKILL)
            run.proc.wait()
            run.logf.write(log_interrupted())
            run.logf.close()
            self._batches.end(addr, ok=False)
            run.killed = True
            self._events.ended(run, run.proc.returncode, error="interrupted by scheduler shutdown")
        self._records.forget(*runs)
        runs.clear()


class PollingRunReaper(RunReaper):
    """One pass over the runs in flight: those that ended are closed, forgotten and settled."""

    def __init__(
        self, watching: RunWatching, records: RunRecords, guard: PhaseGuard, strays: StrayWatch, settling: RunSettling, clock: Clock,
        terminating: RunTerminating,
    ) -> None:
        self._watching, self._records, self._guard, self._strays = watching, records, guard, strays
        self._settling, self._clock, self._terminating = settling, clock, terminating

    def reap(self, runs: RunTable) -> None:
        for addr, run in list(runs.items()):
            exit = self._watching.watch(run)
            if exit is None:
                continue
            elapsed = self._clock.time() - run.started
            run.logf.write(log_exit(exit.code, elapsed))
            self._guard.guard("stray check", lambda: self._strays.after(run))
            run.logf.close()
            del runs[addr]
            self._guard.guard("run record", lambda: self._records.forget(addr))
            self._settling.settle(run, exit, elapsed)

    def terminate_all(self, runs: RunTable) -> None:
        self._terminating.terminate_all(runs)
