"""RED skeleton (B-strays): the ledger of strays."""

from __future__ import annotations

from collections.abc import Sequence

from ..access import ToolNaming
from ..kernel import LedgerStore
from .api import StrayRegistry


class LedgerStrayRegistry(StrayRegistry):
    def __init__(self, ledgers: LedgerStore, naming: ToolNaming) -> None:
        self._ledgers = ledgers
        self._naming = naming

    def record(self, addr: str, paths: Sequence[str]) -> None:
        raise NotImplementedError("red: B-strays")

    def take_notice(self, addr: str) -> str:
        raise NotImplementedError("red: B-strays")
