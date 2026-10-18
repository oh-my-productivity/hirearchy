# mypy: ignore-errors
"""The one-time notice about org files left in a workspace (strays).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations




class StraysMixin:
    """The one-time notice about org files left in a workspace (strays)."""

    def stray_notice(self, addr: str) -> str:
        """The one-time notice for an agent whose built-in ``write`` put org files in its workspace (see the
        scheduler's stray detection). Told once per agent: the ledger entry is marked, nothing is moved or deleted."""
        ledger = self.ledger("strays")
        entry = ledger.get(addr)
        if not isinstance(entry, dict) or entry.get("told") or not entry.get("paths"):
            return ""
        entry["told"] = True
        self.save_ledger("strays", ledger)
        paths = ", ".join(f"`{p}`" for p in entry["paths"][:5])
        wn = self.tool_names(addr)["write"]
        return (
            "# Notice from the runtime (shown once)\n"
            f"A previous run of yours used kiro's built-in `write` and created org files in your WORKSPACE: {paths}. "
            "The organization does not see them, so your org memory and notes are not saved. Move that content into "
            f"your org files now: read it, then save it with `@orgmcp/{wn}` (e.g. path=\"{addr}/MEMORY.md\" or "
            f"\"{addr}/work/...\"). Use `@orgmcp/{wn}` for every org file from now on; the built-in `write` is for the "
            "workspace only. The runtime does not move or delete those files; if they are real workspace "
            "deliverables, ignore this."
        )
