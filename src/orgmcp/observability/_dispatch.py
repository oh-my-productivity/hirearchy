"""One entry point for the text of every view. (RED: skeleton.)"""

from __future__ import annotations

from datetime import datetime

from ..agents import AgentDirectory
from ..eventlog import EventReader
from ..kernel import JsonObject
from ._ports import TargetedEvents
from .api import EventQueries, IntegrityChecks, MetricQueries, NowQueries, ObservabilityRenderer, ObservabilityText, TraceQueries

VIEWS = ("now", "trace", "metrics", "events", "check")


class AgentTargetedEvents(TargetedEvents):
    def __init__(self, events: EventQueries, agents: AgentDirectory, reader: EventReader) -> None:
        self._events, self._agents, self._reader = events, agents, reader

    def view(self, target: str | None, since: str, errors_only: bool, limit: int, now: datetime | None) -> JsonObject:
        raise NotImplementedError("red: C-obs-2")


class ViewDispatcher(ObservabilityText):
    def __init__(
        self, events: TargetedEvents, traces: TraceQueries, metrics: MetricQueries, now: NowQueries, checks: IntegrityChecks,
        renderer: ObservabilityRenderer,
    ) -> None:
        self._events, self._traces, self._metrics, self._now, self._checks, self._renderer = events, traces, metrics, now, checks, renderer

    def observe_text(
        self, view: str = "now", target: str | None = None, since: str = "24h", by: str | None = None, errors_only: bool = False,
        limit: int = 50, now: datetime | None = None, max_lines: int | None = None,
    ) -> str:
        raise NotImplementedError("red: C-obs-2")
