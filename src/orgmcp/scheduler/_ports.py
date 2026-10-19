"""The ports of the run lifecycle: one small Protocol per role, owned by the scheduler because it is their only consumer (ARCHITECTURE.md 3.36).

``RunStarter`` and ``RunReaper`` are what the loop (D-sched-2) holds; the rest are the roles they are made of, put together by ``app.wire_scheduler``.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Sequence
from pathlib import Path
from typing import Protocol

from ..processes import ProcessHandle
from ._run import Exit, PreparedRun, RunRecord, RunTable


class Console(Protocol):
    def say(self, line: str) -> None:
        """One line of the scheduler's output (what ``orgmcp run`` prints)."""
        ...


class PhaseGuard(Protocol):
    def guard(self, phase: str, fn: Callable[[], None]) -> None:
        """Run a best-effort phase; log (once per distinct error) instead of raising out of the loop."""
        ...


class RunEvents(Protocol):
    def started(self, prepared: PreparedRun, pid: int | None) -> None:
        """The ``run.start`` event (``pid`` None: the process never started)."""
        ...

    def ended(self, run: RunRecord, code: int | None, error: str | None = None) -> None:
        """The ``run.end`` event; ``error`` None = derived from the exit code."""
        ...

    def not_started(self, prepared: PreparedRun, error: Exception) -> None:
        """``run.start`` without a process, then ``run.end`` saying that it failed to start."""
        ...


class RunRecords(Protocol):
    def record(self, addr: str, run: RunRecord) -> None:
        """Put the run in the registry of runs in flight (``.runtime/running.json``), which is how a new scheduler finds the runs of a dead one."""
        ...

    def forget(self, *addrs: str) -> None:
        """Take the first of these agents that has a record out of the registry."""
        ...


class RunFailures(Protocol):
    def failed(self, addr: str, log: Path, traces: Sequence[str]) -> None:
        """Count a failed run; at ``max_failures`` in a row pause the agent and tell its parent (and the human)."""
        ...

    def cleared(self, addr: str) -> None:
        """A run succeeded: the count starts again."""
        ...


class FailureEscalation(Protocol):
    def escalate(self, addr: str, count: int, log: Path, traces: Sequence[str]) -> None:
        """Pause the agent and notify when ``count`` reached ``max_failures``."""
        ...


class StrayWatch(Protocol):
    def before(self, addr: str) -> dict[str, float]:
        """Where the agent's built-in ``write`` could leave org files in its workspace, and what is there now."""
        ...

    def after(self, run: RunRecord) -> None:
        """After a run: warn (run log, output, registry) about org files that appeared in the workspace."""
        ...


class RunAdmission(Protocol):
    def admit(self, addr: str) -> bool:
        """May the agent start a run now? Has it waking mail, is it paused, has it budget; pauses and notifies when it is out of budget."""
        ...


class RunPreparation(Protocol):
    def prepare(self, addr: str) -> PreparedRun:
        """Take the batch, create the log, count the run and write the prompt."""
        ...


class RunSpawning(Protocol):
    def spawn(self, prepared: PreparedRun) -> ProcessHandle:
        """Write the header, the command and the prompt into the log, and start the process in its own session with the prompt on its stdin."""
        ...


class StartFailures(Protocol):
    def handle(self, prepared: PreparedRun, error: Exception) -> None:
        """The process could not start: log it, give the batch back, emit the events and count a failed run."""
        ...


class StartAnnouncing(Protocol):
    def announce(self, run: RunRecord, prepared: PreparedRun) -> None:
        """The run started: ``run.start`` event, registry record, output line."""
        ...


class RunInitiation(Protocol):
    def start(self, runs: RunTable, addr: str) -> None:
        """Start one run of the agent, whatever its state; the run joins ``runs`` unless it failed to start."""
        ...


class RunStarter(Protocol):
    def launch(self, runs: RunTable, blocked: Collection[str], max_runs: int | None) -> int:
        """Start runs for the agents that may, up to ``max_parallel`` and ``max_runs`` (the cap on runs started by this scheduler); returns how many."""
        ...

    def start(self, runs: RunTable, addr: str) -> None:
        """Start one run of the agent now (no admission)."""
        ...


class RunWatching(Protocol):
    def watch(self, run: RunRecord) -> Exit | None:
        """Has the run ended? A run past ``run_timeout`` or of a retired agent is killed (its whole process group) and reported as ended."""
        ...


class RunSettling(Protocol):
    def settle(self, run: RunRecord, exit: Exit, elapsed: float) -> None:
        """A run ended: give the batch back or finish it, emit ``run.end``, count the failure or clear it, commit."""
        ...


class RunTerminating(Protocol):
    def terminate_all(self, runs: RunTable) -> None:
        """Interrupt every run in flight (SIGTERM, then SIGKILL of the group), give their batches back and empty the table."""
        ...


class RunReaper(Protocol):
    def reap(self, runs: RunTable) -> None:
        """Collect finished, timed-out and retired runs; settle their batches."""
        ...

    def terminate_all(self, runs: RunTable) -> None:
        """Shutdown: interrupt the runs in flight."""
        ...


__all__ = [
    "Console", "FailureEscalation", "PhaseGuard", "RunAdmission", "RunEvents", "RunFailures", "RunInitiation", "RunPreparation", "RunReaper",
    "RunRecords", "RunSettling", "RunSpawning", "RunStarter", "RunTerminating", "RunWatching", "StartAnnouncing", "StartFailures", "StrayWatch",
]
