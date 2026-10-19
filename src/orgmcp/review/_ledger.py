"""``StoreReviewLedger``: ``.runtime/reviews.json`` (moved from ``review.read_ledger`` and ``review._save``)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from ..kernel import LedgerStore, aware
from ._ports import LedgerRecord, ReviewLedger

LEDGER = "reviews"  # .runtime/reviews.json


class StoreReviewLedger(ReviewLedger):
    def __init__(self, ledgers: LedgerStore) -> None:
        self._ledgers = ledgers

    def read(self) -> LedgerRecord | None:
        """The reviews ledger normalised; None when there is none or it is malformed."""
        ledger = self._ledgers.read(LEDGER)
        if not ledger:
            return None
        raw = ledger.get("notified")
        notified = {k: v for k, v in raw.items() if isinstance(k, str) and isinstance(v, list)} if isinstance(raw, dict) else {}
        runs = ledger.get("runs")
        return LedgerRecord(ledger.get("at"), runs if isinstance(runs, int) and not isinstance(runs, bool) else 0, notified)

    def save(self, at: datetime, runs: int, notified: Mapping[str, list[str]]) -> None:
        aware_at = aware(at)
        assert aware_at is not None
        self._ledgers.write(LEDGER, {"at": aware_at.isoformat(timespec="seconds"), "runs": runs, "notified": {k: list(v) for k, v in notified.items()}})
