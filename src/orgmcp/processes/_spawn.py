"""RED skeleton (step A-processes): the real spawner and handle."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from .api import ProcessHandle, ProcessSpawner


class PopenHandle(ProcessHandle):
    def __init__(self, proc: subprocess.Popen[str]) -> None:
        raise NotImplementedError

    @property
    def pid(self) -> int:
        raise NotImplementedError

    @property
    def returncode(self) -> int | None:
        raise NotImplementedError

    def poll(self) -> int | None:
        raise NotImplementedError

    def wait(self, timeout: float | None = None) -> int:
        raise NotImplementedError

    def signal_group(self, sig: int) -> None:
        raise NotImplementedError


class PopenProcessSpawner(ProcessSpawner):
    def spawn(
        self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], stdin: object | None, stdout: object | None
    ) -> ProcessHandle:
        raise NotImplementedError

    def spawn_detached(self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], log: Path) -> ProcessHandle:
        raise NotImplementedError
