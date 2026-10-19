"""The one-time notice about org files left in a workspace (strays).

The body calls the ports of ``self.runtime`` (step B-strays; ARCHITECTURE.md 5.3 and 6.4)."""

from __future__ import annotations

from .runtime import OrgRuntime


class StraysMixin:
    """The one-time notice about org files left in a workspace (strays)."""

    runtime: OrgRuntime

    def stray_notice(self, addr: str) -> str:
        """The one-time notice for an agent whose built-in ``write`` put org files in its workspace (see the
        scheduler's stray detection). Told once per agent: the ledger entry is marked, nothing is moved or deleted."""
        return self.runtime.stray_registry.take_notice(addr)
