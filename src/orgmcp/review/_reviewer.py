"""``LedgerHealthReviewer``: the health review, from the planner to the ledger (moved from ``review.review`` and ``review.review_if_due``)."""

from __future__ import annotations

from datetime import datetime

from ..kernel import Clock, EventSink, JsonObject
from ._ports import NoteOutbox, ReviewCadence, ReviewLedger, ReviewPlanner, RunTotal
from .api import HealthReviewer, Review


class LedgerHealthReviewer(HealthReviewer):
    def __init__(
        self, planner: ReviewPlanner, ledger: ReviewLedger, runs: RunTotal, cadence: ReviewCadence, outbox: NoteOutbox, events: EventSink,
        clock: Clock,
    ) -> None:
        self._planner = planner
        self._ledger = ledger
        self._runs = runs
        self._cadence = cadence
        self._outbox = outbox
        self._events = events
        self._clock = clock

    def review(self, now: datetime | None = None, dry_run: bool = False) -> Review:
        raise NotImplementedError("red: C-review")

    def review_if_due(self, now: datetime) -> Review | None:
        raise NotImplementedError("red: C-review")

    def total_runs(self) -> int:
        raise NotImplementedError("red: C-review")

    def read_ledger(self) -> JsonObject | None:
        raise NotImplementedError("red: C-review")
