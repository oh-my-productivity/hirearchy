"""The ledger of strays: what was found, until the agent has been told (moved from ``Org.stray_notice`` and ``Scheduler._check_strays``)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from ..access import ToolNaming
from ..kernel import LedgerStore
from .api import StrayRegistry

LEDGER = "strays"


class LedgerStrayRegistry(StrayRegistry):
    """``.runtime/strays.json``: per agent ``{"paths": [...], "told": bool}``."""

    def __init__(self, ledgers: LedgerStore, naming: ToolNaming) -> None:
        self._ledgers = ledgers
        self._naming = naming

    def record(self, addr: str, paths: Sequence[str]) -> None:
        ledger = self._ledgers.read(LEDGER)
        entry = ledger.get(addr)
        if not (isinstance(entry, dict) and entry.get("told")):  # told once per agent: later strays are only logged
            ledger[addr] = {"paths": list(paths)[:10], "told": False}
            self._ledgers.write(LEDGER, ledger)

    def take_notice(self, addr: str) -> str:
        ledger = self._ledgers.read(LEDGER)
        entry = ledger.get(addr)
        if not isinstance(entry, dict) or entry.get("told") or not entry.get("paths"):
            return ""
        entry["told"] = True
        self._ledgers.write(LEDGER, ledger)
        paths = ", ".join(f"`{p}`" for p in cast("Sequence[object]", entry["paths"])[:5])
        wn = self._naming.tool_names(addr)["write"]
        return (
            "# Notice from the runtime (shown once)\n"
            f"A previous run of yours used kiro's built-in `write` and created org files in your WORKSPACE: {paths}. "
            "The organization does not see them, so your org memory and notes are not saved. Move that content into "
            f"your org files now: read it, then save it with `@hirearchy/{wn}` (e.g. path=\"{addr}/MEMORY.md\" or "
            f"\"{addr}/work/...\"). Use `@hirearchy/{wn}` for every org file from now on; the built-in `write` is for the "
            "workspace only. The runtime does not move or delete those files; if they are real workspace "
            "deliverables, ignore this."
        )
