"""``StoreReviewLedger``: ``.runtime/reviews.json`` (moved from ``review.read_ledger`` and ``review._save``)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from ..kernel import JsonObject, LedgerStore
from ._ports import ReviewLedger

LEDGER = "reviews"  # .runtime/reviews.json


class StoreReviewLedger(ReviewLedger):
    def __init__(self, ledgers: LedgerStore) -> None:
        self._ledgers = ledgers

    def read(self) -> JsonObject | None:
        raise NotImplementedError("red: C-review")

    def save(self, at: datetime, runs: int, notified: Mapping[str, list[str]]) -> None:
        raise NotImplementedError("red: C-review")
