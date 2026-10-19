"""(c) Nothing inflight without a live run."""

from __future__ import annotations

from collections.abc import Sequence

from ...agents import AgentDirectory
from ...daemon import SchedulerStatus
from ...kernel import JsonObject
from ...mail import MessageFile
from ...runs import RunRegistry
from .._ports import IntegrityCheck, LiveRuns, MailboxFiles


class InflightAccounted(IntegrityCheck):
    def __init__(self, agents: AgentDirectory, files: MailboxFiles, registry: RunRegistry, live: LiveRuns, scheduler: SchedulerStatus) -> None:
        self._agents, self._files, self._registry, self._live, self._scheduler = agents, files, registry, live, scheduler

    def run(self, files: Sequence[MessageFile], now: float) -> JsonObject:
        raise NotImplementedError("red: C-obs-2")
