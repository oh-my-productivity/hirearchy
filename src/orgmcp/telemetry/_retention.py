"""Deletes the day directories of the event log that expired."""

from __future__ import annotations

from datetime import datetime

from ..kernel import Clock, OrgLayout
from ._pool import DropLog
from .api import EventRetention


class FsEventRetention(EventRetention):
    def __init__(self, layout: OrgLayout, clock: Clock, drops: DropLog) -> None:
        raise NotImplementedError("red: A-telemetry")

    def prune(self, keep_days: int, today: datetime | None = None) -> list[str]:
        raise NotImplementedError("red: A-telemetry")
