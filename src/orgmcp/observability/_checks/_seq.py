"""(e) The event files have no gaps in their line numbers."""

from __future__ import annotations

from collections.abc import Sequence

from ...eventlog import EventReader
from ...kernel import JsonObject
from ...mail import MessageFile
from .._ports import IntegrityCheck


class SeqGapless(IntegrityCheck):
    def __init__(self, events: EventReader) -> None:
        self._events = events

    def run(self, files: Sequence[MessageFile], now: float) -> JsonObject:
        raise NotImplementedError("red: C-obs-2")
