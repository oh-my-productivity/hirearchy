"""Waiting for a scheduler that was just started to be up."""

from __future__ import annotations

from pathlib import Path

from ..kernel import Clock, OrgLayout
from ..processes import ProcessHandle
from ._ports import StartupWatch
from .api import ExitMarker

STARTUP_SECONDS = 10  # how long a scheduler has to write its pid
POLL_SECONDS = 0.05


class PidFileStartupWatch(StartupWatch):
    def __init__(self, layout: OrgLayout, marker: ExitMarker, clock: Clock) -> None:
        self._layout = layout
        self._marker = marker
        self._clock = clock

    def await_start(self, handle: ProcessHandle, log: Path) -> None:
        raise NotImplementedError
