"""The trace of one request. (RED: skeleton.)"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ..agents import AgentDirectory
from ..eventlog import EventReader
from ..kernel import Clock, JsonObject
from ._messages import Msg
from ._ports import MessageHistory, RunCollection, TraceDerivers
from .api import TraceQueries


def run_window(task: Msg, result: Msg | None, root_tasks: Sequence[Msg]) -> tuple[str, str | None]:
    raise NotImplementedError("red: C-obs-1")


def in_window(name: str, start: str, end: str | None) -> bool:
    raise NotImplementedError("red: C-obs-1")


def calls_summary(calls: Sequence[JsonObject]) -> JsonObject:
    raise NotImplementedError("red: C-obs-1")


def user_wait(in_trace: Sequence[Msg], events: Sequence[tuple[datetime, JsonObject]], tid: str, t_end: datetime) -> float:
    raise NotImplementedError("red: C-obs-1")


class DerivedTraceQueries(TraceQueries):
    def __init__(
        self, history: MessageHistory, derivers: TraceDerivers, events: EventReader, runs: RunCollection, agents: AgentDirectory, clock: Clock
    ) -> None:
        self._history, self._derivers, self._events, self._runs, self._agents, self._clock = history, derivers, events, runs, agents, clock

    def trace(self, task_id: str, now: datetime | None = None) -> JsonObject:
        raise NotImplementedError("red: C-obs-1")
