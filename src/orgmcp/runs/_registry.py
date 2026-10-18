"""RED skeleton (step A-runs): the registry of runs in flight (``.runtime/running.json``)."""

from __future__ import annotations

from collections.abc import Mapping

from ..kernel import JsonObject, LedgerStore
from .api import RunRegistry


class FsRunRegistry(RunRegistry):
    def __init__(self, ledgers: LedgerStore) -> None:
        raise NotImplementedError("red: A-runs")

    def all(self) -> dict[str, JsonObject]:
        raise NotImplementedError("red: A-runs")

    def record(self, addr: str, record: JsonObject) -> None:
        raise NotImplementedError("red: A-runs")

    def forget(self, *addrs: str) -> None:
        raise NotImplementedError("red: A-runs")

    def replace(self, records: Mapping[str, JsonObject]) -> None:
        raise NotImplementedError("red: A-runs")
