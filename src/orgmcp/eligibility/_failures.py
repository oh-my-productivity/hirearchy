"""``LedgerFailureCounter``: the consecutive failures of each agent in ``.runtime/failures.json``."""

from __future__ import annotations

from typing import cast

from ..kernel import JsonObject, LedgerStore
from ._ports import LedgerShape
from .api import FailureCounter

LEDGER = "failures"  # .runtime/failures.json


class LedgerFailureCounter(FailureCounter):
    def __init__(self, ledgers: LedgerStore, shape: LedgerShape) -> None:
        self._ledgers = ledgers
        self._shape = shape

    def record(self, addr: str) -> int:
        counts = self._ledgers.read(LEDGER)
        counts[addr] = int(cast(int, counts.get(addr, 0))) + 1
        self._ledgers.write(LEDGER, counts)
        return cast(int, counts[addr])

    def clear(self, addr: str) -> None:
        counts = self._ledgers.read(LEDGER)
        if counts.pop(addr, None) is not None:
            self._ledgers.write(LEDGER, counts)

    def repair(self) -> bool:
        raw = self._ledgers.read(LEDGER)
        clean: JsonObject = {k: v for k, v in raw.items() if isinstance(v, int) and not isinstance(v, bool)}
        if clean != raw or self._shape.damaged(LEDGER):
            self._ledgers.write(LEDGER, clean)
            return True
        return False
