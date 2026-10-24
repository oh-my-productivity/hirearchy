"""Waiting for a scheduler that was just started to be up."""

from __future__ import annotations

from pathlib import Path

from ..kernel import Clock, OrgError, OrgLayout
from ..processes import ProcessInspector, ProcessTableError
from ._files import pidfile_of
from ._ports import StartupWatch
from .api import ExitMarker

STARTUP_SECONDS = 10  # how long a scheduler has to write its pid
POLL_SECONDS = 0.05


class PidFileStartupWatch(StartupWatch):
    """The scheduler is not our child: it is watched through its pid file, the process table and the exit marker. ``prepare()`` clears the marker
    before every launch (``daemon/_site.py``), so any marker was written by this scheduler's own clean exit."""

    def __init__(self, layout: OrgLayout, marker: ExitMarker, clock: Clock, inspector: ProcessInspector) -> None:
        self._layout = layout
        self._marker = marker
        self._clock = clock
        self._inspector = inspector

    def await_start(self, pid: int, log: Path) -> int:
        pidfile = pidfile_of(self._layout)
        deadline = self._clock.time() + STARTUP_SECONDS
        while self._clock.time() < deadline:
            try:
                recorded = int(pidfile.read_text().strip())
            except (OSError, ValueError):
                recorded = None
            if recorded == pid:
                return recorded  # the scheduler's own record of itself
            if self._gone(pid):
                if self._marker.read():
                    return pid  # it had nothing left to do and exited by itself (until-done): that is not a failure
                tail = "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-5:])
                raise OrgError(f"the scheduler exited at once; {log} ends with:\n{tail}")
            self._clock.sleep(POLL_SECONDS)
        return pid  # a slow start

    def _gone(self, pid: int) -> bool:
        try:
            info = self._inspector.info(pid)
        except ProcessTableError:
            return False  # nothing is known about it
        return info is None or info.state.startswith("Z")
