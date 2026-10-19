"""The old module-level names of ``orgmcp.review``, as thin adapters over the reviewer of the organization they are given.

Exported by ``__init__`` until step E3 (``LEGACY_EXPORTS``). Each function takes the ``Org`` it is given (a feature may not import the facade, so it is
duck-typed) and asks the ``HealthReviewer`` of its runtime *at the call*: tests replace ``org.runtime`` under a running scheduler.

``review_if_due`` is what the scheduler calls (``Scheduler._check_review``) and ``review`` what ``orgmcp review`` calls (``cmd_review``), until
steps D-sched-1 and D-cli give them the reviewer through the composition root.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .api import Review

Org = Any  # the facade (a feature may not import it): the functions below take whatever has its runtime

LEDGER = "reviews"


def read_ledger(org: Org) -> dict[str, Any] | None:
    """The reviews ledger normalised to {"at", "runs", "notified"}; None when there is none or it is malformed."""
    ledger: dict[str, Any] | None = org.runtime.health_reviewer.read_ledger()
    return ledger


def total_runs(org: Org) -> int:
    """Runs ever used across the organization, counted from the run logs (so a restart does not reset it).

    Retired agents are included, so retiring never moves the counter backwards (and never postpones a review).
    """
    total: int = org.runtime.health_reviewer.total_runs()
    return total


def review_if_due(org: Org, now: datetime) -> Review | None:
    """Run a review when ``review_every_runs`` runs or ``review_every_seconds`` have passed since the last one.

    With no earlier review the clock starts now (the ledger is created, nothing is reported).
    """
    due: Review | None = org.runtime.health_reviewer.review_if_due(now)
    return due


def review(org: Org, now: datetime | None = None, dry_run: bool = False) -> Review:
    """Review the organization now. With ``dry_run`` nothing is sent and the ledger is left alone."""
    done: Review = org.runtime.health_reviewer.review(now, dry_run)
    return done
