"""``LedgerHealthReviewer``: the health review, from the planner to the ledger (moved from ``review.review`` and ``review.review_if_due``)."""

from __future__ import annotations

from datetime import datetime

from ..kernel import Clock, EventSink, JsonObject, aware
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
        """Review the organization now. With ``dry_run`` nothing is sent and the ledger is left alone."""
        now = aware(now) or self._clock.now()
        last = self._ledger.read()
        result = self._planner.plan(now, last.notified if last else {})
        if not dry_run:
            self._outbox.deliver(result.notes)
            self._ledger.save(now, result.runs, result.notified)
            self._events.emit("review.run", flagged=result.flagged, notes=[n.to for n in result.notes])
        return result

    def review_if_due(self, now: datetime) -> Review | None:
        """Run a review when ``review_every_runs`` runs or ``review_every_seconds`` have passed since the last one.

        With no earlier review the clock starts now (the ledger is created, nothing is reported).
        """
        return self.review(now) if self._cadence.due(now) else None

    def total_runs(self) -> int:
        return self._runs.total()

    def read_ledger(self) -> JsonObject | None:
        """The ledger normalised to {"at", "runs", "notified"}; None when there is none or it is malformed."""
        last = self._ledger.read()
        return {"at": last.at, "runs": last.runs, "notified": last.notified} if last else None
