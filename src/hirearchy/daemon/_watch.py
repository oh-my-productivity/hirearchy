"""Waiting for a scheduler that was just started to be up."""

from __future__ import annotations

from pathlib import Path

from ..kernel import Clock, OrgError, OrgLayout
from ..processes import ProcessHandle
from ._files import pidfile_of
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
        pidfile = pidfile_of(self._layout)
        deadline = self._clock.time() + STARTUP_SECONDS
        while self._clock.time() < deadline:
            code = handle.poll()
            if code == 0 and self._marker.read():
                break  # it had nothing left to do and exited by itself (until-done): that is not a failure
            if code is not None:
                tail = "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-5:])
                raise OrgError(f"the scheduler exited at once (exit {code}); {log} ends with:\n{tail}")
            try:
                if int(pidfile.read_text().strip()) == handle.pid:
                    break
            except (OSError, ValueError):
                pass
            self._clock.sleep(POLL_SECONDS)
