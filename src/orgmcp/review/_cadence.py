"""``LedgerReviewCadence``: when a review is due (moved from the first half of ``review.review_if_due``)."""

from __future__ import annotations

from datetime import datetime

from ..settings import OrgSettings
from ._ports import ReviewCadence, ReviewLedger, RunTotal


class LedgerReviewCadence(ReviewCadence):
    def __init__(self, ledger: ReviewLedger, runs: RunTotal, settings: OrgSettings) -> None:
        self._ledger = ledger
        self._runs = runs
        self._settings = settings

    def due(self, now: datetime) -> bool:
        raise NotImplementedError("red: C-review")
