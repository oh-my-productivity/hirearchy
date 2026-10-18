"""Starting processes: each in its own session, so that a timeout or a shutdown can take the tool subprocesses along."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import IO, Any, cast

from .api import ProcessHandle, ProcessSpawner


class PopenHandle(ProcessHandle):
    """A process started by ``subprocess.Popen``."""

    def __init__(self, proc: subprocess.Popen[str] | subprocess.Popen[bytes]) -> None:
        self._proc = proc

    @property
    def pid(self) -> int:
        return self._proc.pid

    @property
    def returncode(self) -> int | None:
        return self._proc.returncode

    def poll(self) -> int | None:
        return self._proc.poll()

    def wait(self, timeout: float | None = None) -> int:
        return self._proc.wait(timeout=timeout)

    def signal_group(self, sig: int) -> None:
        """Signal a run's whole process group (the run was started in its own session, so pgid == pid)."""
        try:
            os.killpg(self._proc.pid, sig)
        except (ProcessLookupError, PermissionError):
            try:  # the group is gone (or not ours): fall back to the top process
                self._proc.send_signal(sig)
            except (ProcessLookupError, PermissionError):
                pass


class PopenProcessSpawner(ProcessSpawner):
    def spawn(
        self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], stdin: object | None, stdout: object | None
    ) -> ProcessHandle:
        # Its own session/process group, so a timeout or shutdown can take the tool subprocesses along.
        proc = subprocess.Popen(
            list(argv), cwd=cwd, env=dict(env), stdin=cast("IO[Any] | int | None", stdin), stdout=cast("IO[Any] | int | None", stdout),
            stderr=subprocess.STDOUT, text=True, start_new_session=True,
        )
        return PopenHandle(proc)

    def spawn_detached(self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], log: Path) -> ProcessHandle:
        with open(log, "ab") as out:
            proc = subprocess.Popen(
                list(argv), cwd=cwd, env=dict(env), stdin=subprocess.DEVNULL, stdout=out,
                stderr=subprocess.STDOUT, start_new_session=True,
            )
        return PopenHandle(proc)
