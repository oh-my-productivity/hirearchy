"""Run logs (runs).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

from pathlib import Path

from ..kernel import visible as _visible
from ._compat import utcnow


class RunsMixin:
    """Run logs (runs)."""

    def runs_used(self, addr: str) -> int:
        d = self.dir(addr) / "runs"
        return len(_visible(d.glob("*.log"))) if d.is_dir() else 0

    def start_run_log(self, addr: str) -> Path:
        """Create this run's log file. Its existence is what consumes one run of budget."""
        d = self.dir(addr) / "runs"
        d.mkdir(exist_ok=True)
        p = d / f"{utcnow():%Y%m%dT%H%M%S%f}.log"
        p.touch()
        return p
