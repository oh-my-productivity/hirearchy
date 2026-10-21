"""The pidfile as the lock that keeps two schedulers off one organization."""

from __future__ import annotations

from pathlib import Path

from ..kernel import OrgError, OrgLayout
from ..processes import ProcessInspector
from ._files import pidfile_of
from .api import SchedulerLock


class PidFileSchedulerLock(SchedulerLock):
    def __init__(self, layout: OrgLayout, inspector: ProcessInspector) -> None:
        self._layout = layout
        self._inspector = inspector

    def _holder(self, pidfile: Path) -> int | None:
        """The live process the pidfile names, or None when it names none (garbled, or a process that is gone)."""
        try:
            pid = int(pidfile.read_text().strip())
        except ValueError:
            return None
        return pid if pid > 0 and self._inspector.is_alive(pid) else None  # a pid owned by another user is alive too

    def acquire(self) -> None:
        pidfile = pidfile_of(self._layout)
        pidfile.parent.mkdir(parents=True, exist_ok=True)
        if pidfile.exists():
            holder = self._holder(pidfile)
            if holder is not None:
                raise OrgError(f"a scheduler is already running for this org (pid {holder})")
            pidfile.unlink()  # stale
        pidfile.write_text(str(self._inspector.own_ids()[0]))

    def release(self) -> None:
        pidfile_of(self._layout).unlink(missing_ok=True)
