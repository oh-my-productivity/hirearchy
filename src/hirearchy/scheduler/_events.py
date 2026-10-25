"""The events of the scheduler: its own sink (``proc=scheduler``, ``actor=runtime``) and the events of a run's life."""

from __future__ import annotations

import os
from collections.abc import Sequence

from ..access import ModelResolver
from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..kernel import Clock, EventSink, Provider, clip, single
from ..settings import OrgSettings
from ._ports import RunEvents, SessionEvents
from ._run import PreparedRun, RunRecord

ERROR_MAX = 500  # the longest error text that goes into an event


class SchedulerEvents(EventSink):
    """The events of the scheduler process: whoever emits through this says ``proc=scheduler`` and ``actor=runtime`` unless told otherwise."""

    def __init__(self, sink: EventSink) -> None:
        self._sink = sink

    def emit(
        self, kind: str, /, *, actor: str | None = None, run: str | None = None, trace: str | None = None, proc: str | None = None, **fields: object
    ) -> None:
        self._sink.emit(kind, actor=actor or "runtime", run=run, trace=trace, proc=proc or "scheduler", **fields)


class LifecycleEvents(RunEvents):
    """``run.start`` and ``run.end`` with the fields the event log has always carried; the duration is measured with the run clock."""

    def __init__(self, events: EventSink, models: ModelResolver, budgets: BudgetQuery, agents: AgentDirectory, clock: Clock) -> None:
        self._events, self._models, self._budgets, self._agents, self._clock = events, models, budgets, agents, clock

    def started(self, prepared: PreparedRun, pid: int | None) -> None:
        traces = list(prepared.traces)
        self._events.emit("run.start", agent=prepared.addr, run=prepared.run_id, trace=single(traces), batch=[m.id for m in prepared.batch],
                          traces=traces, child_pid=pid, pgid=pid, model=self._models.model_for(prepared.addr),
                          budget_before=prepared.budget_before)

    def ended(self, run: RunRecord, code: int | None, error: str | None = None) -> None:
        ok = code == 0 and not run.killed
        if error is None and not ok:
            error = f"exit code {code}"
        self._events.emit("run.end", agent=run.addr, run=run.run_id, trace=single(run.traces), ok=ok, exit_code=code,
                          duration_ms=int((self._clock.time() - run.started) * 1000), timed_out=run.timed_out, killed=run.killed,
                          budget_after=self._budgets.budget(run.addr) if self._agents.exists(run.addr) else None,
                          error=clip(error, ERROR_MAX) if error else None)

    def not_started(self, prepared: PreparedRun, error: Exception) -> None:
        self.started(prepared, None)
        self._events.emit("run.end", agent=prepared.addr, run=prepared.run_id, ok=False, exit_code=None, duration_ms=0, timed_out=False,
                          killed=False, budget_after=self._budgets.budget(prepared.addr), error=clip(f"failed to start: {error}", ERROR_MAX))


class SessionAnnouncer(SessionEvents):
    """``scheduler.start``, ``scheduler.exit`` and ``scheduler.signal``."""

    def __init__(self, events: EventSink, settings: OrgSettings, version: Provider[str]) -> None:
        self._events, self._settings, self._version = events, settings, version

    def started(self, mode: str, max_runs: int | None) -> None:
        self._events.emit("scheduler.start", mode=mode, max_runs=max_runs, max_parallel=self._settings.number("max_parallel", int),
                          version=self._version())

    def exited(self, reason: str, runs_started: int) -> None:
        self._events.emit("scheduler.exit", reason=clip(reason, ERROR_MAX), runs_started=runs_started)

    def signalled(self, name: str, action: str, running: Sequence[str]) -> None:
        self._events.emit("scheduler.signal", signal=name, action=action, ppid=os.getppid(), running=list(running))
