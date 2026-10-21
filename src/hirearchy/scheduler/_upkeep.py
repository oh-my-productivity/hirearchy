"""The upkeep of a running scheduler: the heartbeat event and the daily pruning of the event log."""

from __future__ import annotations

from ..attention import HumanQueue
from ..eligibility import RunnableQuery
from ..kernel import Clock, EventSink
from ..settings import OrgSettings
from ..telemetry import EventRetention
from ._ports import TickPhase
from ._run import Standing, UpkeepMemory


def package_version() -> str:
    """The installed version of hirearchy (``unknown`` when there is no metadata)."""
    try:
        from importlib.metadata import version

        return version("hirearchy")
    except Exception:  # noqa: BLE001
        return "unknown"


class HeartbeatUpkeep(TickPhase):
    """The heartbeat event (every ``heartbeat_seconds``) and the daily pruning of old event-log days."""

    def __init__(
        self, clock: Clock, settings: OrgSettings, events: EventSink, retention: EventRetention, queue: HumanQueue, runnable: RunnableQuery,
        memory: UpkeepMemory,
    ) -> None:
        self._clock, self._settings, self._events, self._retention = clock, settings, events, retention
        self._queue, self._runnable, self._memory = queue, runnable, memory

    def run(self, standing: Standing, max_runs: int | None) -> None:
        now, memory = self._clock.time(), self._memory
        if memory.heartbeat_at is None or now - memory.heartbeat_at >= self._settings.number("heartbeat_seconds"):
            memory.heartbeat_at = now
            self._events.emit("scheduler.heartbeat", running=sorted(r.run_id for r in standing.runs.values()),
                              runnable=len(self._runnable.runnable(exclude=set(standing.runs) | standing.blocked)),
                              waiting_on_you=len(self._queue.items()))
        if memory.pruned_at is None or now - memory.pruned_at >= 86400:
            memory.pruned_at = now
            removed = self._retention.prune(int(self._settings.number("events_keep_days", int)))
            if removed:
                self._events.emit("prune", removed_days=removed)
