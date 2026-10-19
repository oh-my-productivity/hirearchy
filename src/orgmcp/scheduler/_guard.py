"""The guard of the best-effort phases: a fault in one is logged once and never stops the loop."""

from __future__ import annotations

from collections.abc import Callable

from ..kernel import Clock, EventSink
from ._ports import Console, PhaseGuard
from ._run import GuardMemory


class LoggingPhaseGuard(PhaseGuard):
    def __init__(self, console: Console, events: EventSink, clock: Clock, memory: GuardMemory) -> None:
        raise NotImplementedError("red: D-sched-2")

    def guard(self, phase: str, fn: Callable[[], None]) -> None:
        raise NotImplementedError("red: D-sched-2")
