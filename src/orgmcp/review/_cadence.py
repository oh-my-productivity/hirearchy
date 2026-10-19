"""``LedgerReviewCadence``: when a review is due (moved from the first half of ``review.review_if_due``)."""

from __future__ import annotations

from datetime import datetime

from ..kernel import aware, parse_time
from ..settings import OrgSettings
from ._ports import ReviewCadence, ReviewLedger, RunTotal


class LedgerReviewCadence(ReviewCadence):
    def __init__(self, ledger: ReviewLedger, runs: RunTotal, settings: OrgSettings) -> None:
        self._ledger = ledger
        self._runs = runs
        self._settings = settings

    def due(self, now: datetime) -> bool:
        last = self._ledger.read()
        if not last:  # missing, empty or malformed: the clock starts now
            self._ledger.save(now, self._runs.total(), {})
            return False
        at = parse_time(last.at)
        used = self._runs.total()
        baseline = last.runs
        if used < baseline:  # logs vanished some other way (e.g. .retired/ deleted): start counting again from here
            baseline = used
            self._ledger.save(parse_time(last.at) or now, used, last.notified)
        runs_due = used - baseline >= self._settings.number("review_every_runs", int)
        time_due = at is None or (aware(now) - at).total_seconds() >= self._settings.number("review_every_seconds")
        return bool(runs_due or time_due)
