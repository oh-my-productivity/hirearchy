"""The registry of runs in flight (``.runtime/running.json``)."""

from __future__ import annotations

from collections.abc import Mapping

from ..kernel import JsonObject, LedgerStore
from .api import RunRegistry

LEDGER = "running"  # the name of the ledger (ARCHITECTURE.md 2.3: it belongs to this package)


class FsRunRegistry(RunRegistry):
    def __init__(self, ledgers: LedgerStore) -> None:
        self._ledgers = ledgers

    def all(self) -> dict[str, JsonObject]:
        raw = self._ledgers.read(LEDGER)
        return {k: v for k, v in (raw.items() if isinstance(raw, dict) else ()) if isinstance(v, dict)}

    def record(self, addr: str, record: JsonObject) -> None:
        records = self.all()
        records[addr] = record
        self._ledgers.write(LEDGER, dict(records))

    def forget(self, *addrs: str) -> None:
        records = self.all()
        if any(records.pop(a, None) is not None for a in addrs):  # stops at the first record found, as the scheduler always did
            self._ledgers.write(LEDGER, dict(records))

    def replace(self, records: Mapping[str, JsonObject]) -> None:
        self._ledgers.write(LEDGER, dict(records))
