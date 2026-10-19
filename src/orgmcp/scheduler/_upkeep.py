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
    raise NotImplementedError("red: D-sched-2")


class HeartbeatUpkeep(TickPhase):
    def __init__(
        self, clock: Clock, settings: OrgSettings, events: EventSink, retention: EventRetention, queue: HumanQueue, runnable: RunnableQuery,
        memory: UpkeepMemory,
    ) -> None:
        raise NotImplementedError("red: D-sched-2")

    def run(self, standing: Standing, max_runs: int | None) -> None:
        raise NotImplementedError("red: D-sched-2")
