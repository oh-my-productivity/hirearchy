"""The metrics over a time window. (RED: skeleton.)"""

from __future__ import annotations

from datetime import datetime

from ..eventlog import EventReader
from ..kernel import Clock, JsonObject
from ._ports import MessageHistory, RunCollection
from .api import MetricQueries


class DerivedMetricQueries(MetricQueries):
    def __init__(self, events: EventReader, runs: RunCollection, history: MessageHistory, clock: Clock) -> None:
        self._events, self._runs, self._history, self._clock = events, runs, history, clock

    def metrics(self, since: str | datetime | None = "24h", by: str | None = None, now: datetime | None = None, agent: str | None = None) -> JsonObject:
        raise NotImplementedError("red: C-obs-1")
