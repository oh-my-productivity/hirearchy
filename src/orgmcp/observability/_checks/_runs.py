"""(d) Runs accounted for."""

from __future__ import annotations

from collections.abc import Sequence

from ...agents import AgentDirectory
from ...eventlog import EventReader
from ...kernel import JsonObject
from ...mail import MessageFile
from ...runs import RunLogReader, RunRegistry
from .._ports import IntegrityCheck, LiveRuns


class RunsAccounted(IntegrityCheck):
    def __init__(self, events: EventReader, registry: RunRegistry, live: LiveRuns, agents: AgentDirectory, run_logs: RunLogReader) -> None:
        self._events, self._registry, self._live, self._agents, self._run_logs = events, registry, live, agents, run_logs

    def run(self, files: Sequence[MessageFile], now: float) -> JsonObject:
        raise NotImplementedError("red: C-obs-2")
