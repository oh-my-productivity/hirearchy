"""Starting runs: the agents that may, one run each - its batch, log, prompt, process and the account of it."""

from __future__ import annotations

import tempfile
from collections.abc import Collection

from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..kernel import Clock
from ..kiro import RunCommandBuilder
from ..mail import BatchStore
from ..processes import ProcessHandle, ProcessSpawner
from ..prompts import RunPromptBuilder
from ..runs import RunLogWriter, log_failed_start, log_header, log_invocation, log_prompt, run_id_of
from ..settings import OrgSettings
from ._ports import (
    Console,
    PhaseGuard,
    RunAdmission,
    RunEvents,
    RunFailures,
    RunInitiation,
    RunPreparation,
    RunRecords,
    RunSpawning,
    RunStarter,
    StartAnnouncing,
    StartFailures,
    StrayWatch,
)
from ._run import PreparedRun, RunCount, RunRecord, RunTable


class BatchPreparer(RunPreparation):
    """Takes the batch, creates the log (its existence consumes one run of budget), counts the run and writes the prompt."""

    def __init__(self, batches: BatchStore, budgets: BudgetQuery, logs: RunLogWriter, prompts: RunPromptBuilder, count: RunCount) -> None:
        self._batches, self._budgets, self._logs, self._prompts, self._count = batches, budgets, logs, prompts, count

    def prepare(self, addr: str) -> PreparedRun:
        batch = self._batches.begin(addr)
        budget_before = self._budgets.budget(addr)  # before the run log exists: that is what consumes the run
        log = self._logs.create(addr)
        run_id = run_id_of(addr, log)
        traces = tuple(sorted({m.trace for m in batch if m.trace}))
        self._count.total += 1
        prompt = self._prompts.run_prompt(addr, batch)
        sink = self._logs.open_sink(log)
        return PreparedRun(addr, batch, budget_before, log, sink, run_id, traces, prompt)


class CommandSpawner(RunSpawning):
    """Writes what the run is into its log, then starts the process in its own session, its output going to the log and the prompt to its stdin."""

    def __init__(self, commands: RunCommandBuilder, spawner: ProcessSpawner) -> None:
        self._commands, self._spawner = commands, spawner

    def spawn(self, prepared: PreparedRun) -> ProcessHandle:
        sink = prepared.sink
        sink.write(log_header(prepared.addr, len(prepared.batch), (m.sender for m in prepared.batch)))  # health tells runtime-only runs apart by the senders
        command = self._commands.build(prepared.addr, prepared.prompt)
        env = {**command.env, "ORG_RUN_ID": prepared.run_id}  # the agent's MCP server tags its events with it
        sink.write(log_invocation(command.cwd, list(command.argv)))
        sink.write(log_prompt(prepared.prompt))
        sink.flush()
        with tempfile.TemporaryFile() as stdin:  # a file, not a pipe: no deadlock if the child never reads it
            stdin.write(prepared.prompt.encode("utf-8"))
            stdin.seek(0)
            # Its own session/process group, so a timeout or shutdown can take the tool subprocesses along.
            return self._spawner.spawn(command.argv, cwd=command.cwd, env=env, stdin=stdin, stdout=sink)


class StartFailureHandler(StartFailures):
    def __init__(self, batches: BatchStore, events: RunEvents, failures: RunFailures) -> None:
        self._batches, self._events, self._failures = batches, events, failures

    def handle(self, prepared: PreparedRun, error: Exception) -> None:
        prepared.sink.write(log_failed_start(error))
        prepared.sink.close()
        self._batches.end(prepared.addr, ok=False)
        self._events.not_started(prepared, error)
        self._failures.failed(prepared.addr, prepared.log, prepared.traces)


class StartAnnouncer(StartAnnouncing):
    def __init__(self, events: RunEvents, records: RunRecords, guard: PhaseGuard, console: Console) -> None:
        self._events, self._records, self._guard, self._console = events, records, guard, console

    def announce(self, run: RunRecord, prepared: PreparedRun) -> None:
        self._events.started(prepared, run.proc.pid)
        self._guard.guard("run record", lambda: self._records.record(run.addr, run))
        self._console.say(f"{run.addr}: started run ({len(prepared.batch)} message(s))")


class SingleRunStarter(RunInitiation):
    def __init__(
        self, preparation: RunPreparation, spawning: RunSpawning, strays: StrayWatch, guard: PhaseGuard, failures: StartFailures,
        announcing: StartAnnouncing, clock: Clock,
    ) -> None:
        self._preparation, self._spawning, self._strays, self._guard = preparation, spawning, strays, guard
        self._failures, self._announcing, self._clock = failures, announcing, clock

    def start(self, runs: RunTable, addr: str) -> None:
        prepared = self._preparation.prepare(addr)
        before: list[dict[str, float]] = []
        self._guard.guard("stray check", lambda: before.append(self._strays.before(addr)))
        try:
            proc = self._spawning.spawn(prepared)
        except Exception as exc:  # e.g. kiro-cli missing: count it as a failed run
            self._failures.handle(prepared, exc)
            return
        run = RunRecord(addr, proc, prepared.log, prepared.sink, self._clock.time(), len(prepared.batch), before[0] if before else None,
                        prepared.run_id, prepared.traces, prepared.budget_before)
        runs[addr] = run
        self._announcing.announce(run, prepared)


class AgentRunLauncher(RunStarter):
    def __init__(self, agents: AgentDirectory, settings: OrgSettings, admission: RunAdmission, initiation: RunInitiation, count: RunCount) -> None:
        self._agents, self._settings, self._admission, self._initiation, self._count = agents, settings, admission, initiation, count

    def launch(self, runs: RunTable, blocked: Collection[str], max_runs: int | None) -> int:
        started = 0
        parallel = self._settings.number("max_parallel", int)
        for addr in self._agents.agents():
            if len(runs) >= parallel:
                return started
            if max_runs is not None and self._count.total >= max_runs:
                return started
            if addr in runs or addr in blocked or not self._admission.admit(addr):
                continue
            self._initiation.start(runs, addr)
            started += 1
        return started

    def start(self, runs: RunTable, addr: str) -> None:
        self._initiation.start(runs, addr)
