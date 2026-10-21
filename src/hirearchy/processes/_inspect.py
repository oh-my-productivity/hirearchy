"""The process table as ``ps`` and the system calls report it."""

from __future__ import annotations

import os
import subprocess

from hirearchy.kernel import Environment

from .api import ProcessInfo, ProcessInspector, ProcessTableError


class PsProcessInspector(ProcessInspector):
    def __init__(self, environment: Environment) -> None:
        self._environment = environment

    def info(self, pid: int) -> ProcessInfo | None:
        # the same text for the same process, whatever the caller's locale
        env = {**self._environment.variables(), "LC_ALL": "C", "TZ": "UTC"}
        try:
            out = subprocess.run(["ps", "-o", "stat=,lstart=", "-p", str(pid)], capture_output=True, text=True,
                                 timeout=10, env=env).stdout.split()
        except (OSError, subprocess.SubprocessError) as exc:
            raise ProcessTableError(f"ps could not be run: {exc}") from exc
        return ProcessInfo(out[0], " ".join(out[1:])) if len(out) > 1 else None

    def command_line(self, pid: int) -> str | None:
        try:
            out = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True, timeout=10,
                                 env={**self._environment.variables(), "LC_ALL": "C"}).stdout
        except (OSError, subprocess.SubprocessError):
            return None
        return out.strip() or None

    def start_time(self, pid: int) -> str | None:
        try:
            info = self.info(pid)
        except ProcessTableError:
            return None
        return info.started if info else None

    def is_session_leader(self, pgid: int) -> bool | None:
        try:
            return os.getpgid(pgid) == pgid and os.getsid(pgid) == pgid
        except (ProcessLookupError, PermissionError):
            return None

    def is_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:  # the pid exists but belongs to another user: it is alive
            return True
        return True

    def own_ids(self) -> tuple[int, int]:
        return os.getpid(), os.getpgrp()
