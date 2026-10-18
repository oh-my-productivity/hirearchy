"""Signals to processes and process groups."""

from __future__ import annotations

import os
import signal

from orgmcp.kernel import Clock

from .api import ProcessDenied, ProcessGone, ProcessInspector, ProcessSignaller, ProcessTableError


class OsProcessSignaller(ProcessSignaller):
    def __init__(self, inspector: ProcessInspector, clock: Clock) -> None:
        self._inspector = inspector
        self._clock = clock

    def _refused(self, pid: int) -> bool:
        """pid 0 and negative pids address a whole group or everything, 1 is init, and this process and its group are the caller's."""
        return pid <= 1 or pid in self._inspector.own_ids()

    def kill_group(self, pgid: int, wait: float = 5.0) -> bool:
        """SIGKILL a process group and wait until its leader is gone. True when it is."""
        if self._refused(pgid):
            return False
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        deadline = self._clock.time() + wait
        while self._clock.time() < deadline:
            try:
                info = self._inspector.info(pgid)
            except ProcessTableError:
                return False
            if info is None or info.state.startswith("Z"):
                return True
            self._clock.sleep(0.05)
        return False

    def terminate(self, pid: int) -> None:
        if self._refused(pid):
            raise ProcessDenied(f"not signalling pid {pid}")
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError as exc:
            raise ProcessGone(f"pid {pid} is already gone") from exc
        except PermissionError as exc:
            raise ProcessDenied(f"not allowed to signal pid {pid}") from exc
