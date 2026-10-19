"""Starting runs: the agents that may, one run each - its batch, log, prompt, process and the account of it."""

from __future__ import annotations

from collections.abc import Collection

from ..agents import AgentDirectory
from ..kernel import Clock
from ..mail import BatchStore
from ..budget import BudgetQuery
from ..kiro import RunCommandBuilder
from ..processes import ProcessHandle, ProcessSpawner
from ..prompts import RunPromptBuilder
from ..runs import RunLogWriter
from ..settings import OrgSettings
from ._events import LifecycleEvents  # noqa: F401
from ._ports import (
    PhaseGuard, RunAdmission, RunEvents, RunFailures, RunInitiation, RunPreparation, RunRecords, RunSpawning, RunStarter, StartAnnouncing,
    StartFailures, StrayWatch, Console,
)
from ._run import PreparedRun, RunCount, RunRecord, RunTable


class BatchPreparer(RunPreparation):
    def __init__(self, batches: BatchStore, budgets: BudgetQuery, logs: RunLogWriter, prompts: RunPromptBuilder, count: RunCount) -> None:
        raise NotImplementedError("red: D-sched-1")

    def prepare(self, addr: str) -> PreparedRun:
        raise NotImplementedError("red: D-sched-1")


class CommandSpawner(RunSpawning):
    def __init__(self, commands: RunCommandBuilder, spawner: ProcessSpawner) -> None:
        raise NotImplementedError("red: D-sched-1")

    def spawn(self, prepared: PreparedRun) -> ProcessHandle:
        raise NotImplementedError("red: D-sched-1")


class StartFailureHandler(StartFailures):
    def __init__(self, batches: BatchStore, events: RunEvents, failures: RunFailures) -> None:
        raise NotImplementedError("red: D-sched-1")

    def handle(self, prepared: PreparedRun, error: Exception) -> None:
        raise NotImplementedError("red: D-sched-1")


class StartAnnouncer(StartAnnouncing):
    def __init__(self, events: RunEvents, records: RunRecords, guard: PhaseGuard, console: Console) -> None:
        raise NotImplementedError("red: D-sched-1")

    def announce(self, run: RunRecord, prepared: PreparedRun) -> None:
        raise NotImplementedError("red: D-sched-1")


class SingleRunStarter(RunInitiation):
    def __init__(
        self, preparation: RunPreparation, spawning: RunSpawning, strays: StrayWatch, guard: PhaseGuard, failures: StartFailures,
        announcing: StartAnnouncing, clock: Clock,
    ) -> None:
        raise NotImplementedError("red: D-sched-1")

    def start(self, runs: RunTable, addr: str) -> None:
        raise NotImplementedError("red: D-sched-1")


class AgentRunLauncher(RunStarter):
    def __init__(self, agents: AgentDirectory, settings: OrgSettings, admission: RunAdmission, initiation: RunInitiation, count: RunCount) -> None:
        raise NotImplementedError("red: D-sched-1")

    def launch(self, runs: RunTable, blocked: Collection[str], max_runs: int | None) -> int:
        raise NotImplementedError("red: D-sched-1")

    def start(self, runs: RunTable, addr: str) -> None:
        raise NotImplementedError("red: D-sched-1")
