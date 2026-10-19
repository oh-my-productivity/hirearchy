"""(f) The scheduler's pid file matches a live scheduler."""

from __future__ import annotations

from collections.abc import Sequence

from ...daemon import SchedulerStatus
from ...kernel import JsonObject
from ...mail import MessageFile
from .._ports import IntegrityCheck, SchedulerPidFile


class PidfileSane(IntegrityCheck):
    def __init__(self, pidfile: SchedulerPidFile, scheduler: SchedulerStatus) -> None:
        self._pidfile, self._scheduler = pidfile, scheduler

    def run(self, files: Sequence[MessageFile], now: float) -> JsonObject:
        raise NotImplementedError("red: C-obs-2")
