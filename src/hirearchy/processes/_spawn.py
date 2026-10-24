"""Starting processes: each in its own session, so that a timeout or a shutdown can take the tool subprocesses along."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import IO, Any, cast

from .api import ProcessHandle, ProcessSpawner

DETACH_SECONDS = 10  # how long the intermediate has to report the pid
MESSAGE_CUT = 200  # the reason of a failure is clipped to this many characters


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

    def spawn_detached(self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], log: Path) -> int:
        # An intermediate process (``_detach.py``) starts ``argv`` and exits at once, so ``argv`` is re-parented and is no descendant of this process.
        command = [sys.executable, "-I", str(Path(__file__).with_name("_detach.py")), str(log), "--", *argv]
        try:
            proc = subprocess.Popen(
                command, cwd=cwd, env=dict(env), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                start_new_session=True,
            )
        except OSError as error:
            raise _not_started(argv, str(error)) from error
        try:
            out, err = proc.communicate(timeout=DETACH_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()  # reaped
            raise _not_started(argv, f"no pid was reported within {DETACH_SECONDS} seconds") from None
        words = out.split()
        if proc.returncode != 0 or len(words) != 1 or not words[0].isdigit() or int(words[0]) < 1:
            lines = [line for line in err.splitlines() if line.strip()]
            raise _not_started(argv, lines[-1] if lines else f"the intermediate exited with {proc.returncode} and reported no pid")
        return int(words[0])


def _not_started(argv: Sequence[str], reason: str) -> OSError:
    return OSError(f"could not start {argv[0] if argv else '(nothing)'} detached: {reason[:MESSAGE_CUT]}")
