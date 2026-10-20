"""Clocks for tests that need the time of the organization to be somebody's choice (the seam is ``wiring.overriding``, see fixtures.py)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from orgmcp.kernel import Clock
from orgmcp.kernel._system import SystemClock
from orgmcp.telemetry._ports import EventClock


class ClockReading(SystemClock):
    """The system clock whose ``now()`` is ``reading()``: what a test that replaced ``orgmcp.core.utcnow`` had. ``time``, ``monotonic`` and ``sleep`` are the
    system's: they time waits and files, not the stamps of messages."""

    def __init__(self, reading: Callable[[], datetime]) -> None:
        self._reading = reading

    def now(self) -> datetime:
        return self._reading()


def clock_ports(reading: Callable[[], datetime], events: bool = False) -> dict[type, object]:
    """The ports that make ``reading()`` the time of the runtimes: their ``Clock`` and, with ``events``, the clock the events are stamped with.

    The events keep the system's time by default (as they always did): a clock that moves with every reading (the scenarios') would otherwise be moved
    by every event that is emitted, and the ids of the scenario would not be the ones its expected texts hold."""
    clock = ClockReading(reading)
    return {Clock: clock, EventClock: clock} if events else {Clock: clock}
