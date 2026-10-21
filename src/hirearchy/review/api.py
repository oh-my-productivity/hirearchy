"""The public surface of ``review``: turns the health of the organization into short notes for the managers who can act on it.

``HealthReviewer.review`` is the one code path (the scheduler and ``hirearchy review`` both use it); the scheduler only decides *when*
(``review_if_due``). Healthy parts of the organization cost nothing: a manager is written to only when a direct report has a problem it has not
been told about, and each note costs that manager one run.

* a manager (an agent with direct reports) hears about each (report, flag) pair once; a pair it was already told about in the previous review is
  not repeated. Paused managers and managers whose budget is no more than their outstanding delegations (the reserve for processing results) are
  skipped and listed in root's note;
* root hears about every flagged agent in one note, every review (it is free), so nothing is hidden;
* the only state is ``.runtime/reviews.json``: when, the org-wide run count, and who was told about what.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from ..kernel import JsonObject

__all__ = [
    "HealthReviewer",
    "Note",
    "Review",
    "ReviewReport",
]


@dataclass
class Note:
    to: str
    title: str
    body: str


@runtime_checkable
class ReviewReport(Protocol):
    """What a review can show of itself besides its numbers (``Review`` subclasses it)."""

    def render(self, dry_run: bool = False) -> str:
        """What was (or, for a dry run, would be) sent to whom."""
        ...


@dataclass
class Review(ReviewReport):
    at: datetime
    runs: int  # runs used across the organization when the review ran
    flagged: int  # agents with at least one flag
    notes: list[Note] = field(default_factory=list)
    notified: dict[str, list[str]] = field(default_factory=dict)  # recipient -> "agent:flag" pairs it knows about
    skipped: dict[str, str] = field(default_factory=dict)  # manager with news -> why it was not written to

    def render(self, dry_run: bool = False) -> str:
        """What was (or, for a dry run, would be) sent to whom."""
        if not self.notes:
            return f"{self.flagged} flagged agent(s); nothing to send"
        verb = "would send" if dry_run else "sent"
        out = [f"{self.flagged} flagged agent(s); {verb} {len(self.notes)} note(s)"]
        for n in self.notes:
            out.append(f"\n-> {n.to}: {n.title}\n" + "\n".join(("   " + line).rstrip() for line in n.body.splitlines()))
        return "\n".join(out)


@runtime_checkable
class HealthReviewer(Protocol):
    def review(self, now: datetime | None = None, dry_run: bool = False) -> Review:
        """Review the organization now (``now`` defaults to the clock; a naive time is taken as UTC): write a note to each manager that has a
        problem among its direct reports it was not told about, and one to root about every flagged agent, record who knows what in the ledger
        and emit ``review.run``. With ``dry_run`` nothing is sent, nothing is recorded and nothing is emitted: the review only says what it would do."""
        ...

    def review_if_due(self, now: datetime) -> Review | None:
        """Review when ``review_every_runs`` runs (organization-wide, retired agents included) or ``review_every_seconds`` have passed since the
        last review, else ``None``. With no ledger (or a malformed one) the clock starts now: the ledger is created and nothing is reported. A run
        count that went down (run logs vanished) rebases the ledger on the count seen."""
        ...

    def total_runs(self) -> int:
        """Runs ever used across the organization, counted from the run logs (a restart does not reset it); retired agents are included, so
        retiring never moves the counter backwards."""
        ...

    def read_ledger(self) -> JsonObject | None:
        """The ledger normalised to ``{"at", "runs", "notified"}``; ``None`` when there is none or it is malformed (not an object, empty)."""
        ...
