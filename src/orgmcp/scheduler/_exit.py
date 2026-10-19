"""When a serving scheduler stops by itself: idle, finished, or waiting on the user for longer than the grace period."""

from __future__ import annotations

from ..daemon import ExitMarker
from ..kernel import Clock
from ..settings import OrgSettings
from ._ports import Console, ExitPolicy, WaitGrace, WorkLeft
from ._run import GraceMemory, Standing, StopWhen


class GraceWait(WaitGrace):
    def __init__(self, work: WorkLeft, settings: OrgSettings, clock: Clock, console: Console, memory: GraceMemory) -> None:
        raise NotImplementedError("red: D-sched-2")

    def check(self, standing: Standing) -> str:
        raise NotImplementedError("red: D-sched-2")


class GraceExitPolicy(ExitPolicy):
    def __init__(self, work: WorkLeft, grace: WaitGrace, marker: ExitMarker, console: Console) -> None:
        raise NotImplementedError("red: D-sched-2")

    def after_tick(self, stop: StopWhen, active: bool, standing: Standing) -> str | None:
        raise NotImplementedError("red: D-sched-2")
