"""``SubprocessKiroCli``: a short kiro-cli command with a deadline (docs/design/kiro-runtime-v3.md 13.2)."""

from __future__ import annotations

import os
import signal
import subprocess
from collections.abc import Mapping, Sequence

from .api import CliResult, KiroCli

MAX_OUTPUT = 64 * 1024  # characters of output kept


class SubprocessKiroCli(KiroCli):
    def run(self, argv: Sequence[str], env: Mapping[str, str], timeout: float) -> CliResult | None:
        try:
            proc = subprocess.Popen(
                list(argv), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=dict(env), start_new_session=True
            )
        except (OSError, ValueError):
            return None
        try:
            output, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)  # the command and everything it started
            except OSError:
                proc.kill()
            try:
                proc.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                pass
            return None
        return CliResult(proc.returncode, output.decode("utf-8", errors="replace")[:MAX_OUTPUT])
