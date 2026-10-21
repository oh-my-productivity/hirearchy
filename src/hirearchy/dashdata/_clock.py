"""The time of the dashboard: the clock's, or the one the dashboard was given."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from ..kernel import Clock, aware
from ._ports import DashClock


class ClockDashTime(DashClock):
    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def now(self) -> datetime:
        return aware(self._clock.now())

    def monotonic(self) -> float:
        return self._clock.monotonic()


class GivenDashTime(DashClock):
    """The dashboard shows the time ``now`` returns (a test, a screenshot); how long an answer is kept is still the clock's business."""

    def __init__(self, now: Callable[[], datetime], clock: Clock) -> None:
        self._now = now
        self._clock = clock

    def now(self) -> datetime:
        return aware(self._now())

    def monotonic(self) -> float:
        return self._clock.monotonic()


@dataclass(frozen=True)
class DashSettings:
    """How a dashboard is run: how long the state of the scheduler is trusted before it is asked again."""

    scheduler_ttl: float = 3.0
