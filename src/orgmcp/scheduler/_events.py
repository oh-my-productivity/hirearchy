"""The events of the scheduler: its own sink (``proc=scheduler``, ``actor=runtime``) and the events of a run's life."""

from __future__ import annotations

from ..access import ModelResolver
from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..kernel import Clock, EventSink
from ._ports import RunEvents
from ._run import PreparedRun, RunRecord

ERROR_MAX = 500  # the longest error text that goes into an event


class SchedulerEvents(EventSink):
    """The events of the scheduler process: whoever emits through this says ``proc=scheduler`` and ``actor=runtime`` unless told otherwise."""

    def __init__(self, sink: EventSink) -> None:
        raise NotImplementedError("red: D-sched-1")

    def emit(
        self, kind: str, /, *, actor: str | None = None, run: str | None = None, trace: str | None = None, proc: str | None = None, **fields: object
    ) -> None:
        raise NotImplementedError("red: D-sched-1")


class LifecycleEvents(RunEvents):
    """``run.start`` and ``run.end`` with the fields the event log has always carried; the duration is measured with the run clock."""

    def __init__(self, events: EventSink, models: ModelResolver, budgets: BudgetQuery, agents: AgentDirectory, clock: Clock) -> None:
        raise NotImplementedError("red: D-sched-1")

    def started(self, prepared: PreparedRun, pid: int | None) -> None:
        raise NotImplementedError("red: D-sched-1")

    def ended(self, run: RunRecord, code: int | None, error: str | None = None) -> None:
        raise NotImplementedError("red: D-sched-1")

    def not_started(self, prepared: PreparedRun, error: Exception) -> None:
        raise NotImplementedError("red: D-sched-1")
