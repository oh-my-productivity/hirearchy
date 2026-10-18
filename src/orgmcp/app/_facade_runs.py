"""Run logs (runs).

The bodies call the ports of ``self.runtime`` (step A-runs; ARCHITECTURE.md 5.3 and 6.4)."""

from __future__ import annotations

from pathlib import Path

from .runtime import OrgRuntime


class RunsMixin:
    """Run logs (runs)."""

    runtime: OrgRuntime

    def runs_used(self, addr: str) -> int:
        return self.runtime.run_log_reader.count(addr)

    def start_run_log(self, addr: str) -> Path:
        """Create this run's log file. Its existence is what consumes one run of budget."""
        return self.runtime.run_log_writer.create(addr)
