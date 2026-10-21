"""``review`` as the tests call it (``review(org, now, dry_run=True)``, ``review_if_due(org, now)`` ...): over the ``HealthReviewer`` of the runtime of the organization.

The package's interface is a method of the reviewer of one organization; a test passes the organization first, as it always did.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from hirearchy.review import Review
from hirearchy.templates._notices import REVIEW_ACTIONS as REVIEW_ACTIONS  # what a review tells a manager to do about each flag: not in the api of templates

LEDGER = "reviews"  # .runtime/reviews.json


def review(org: Any, now: datetime | None = None, dry_run: bool = False) -> Review:
    return org.runtime.health_reviewer.review(now, dry_run)  # type: ignore[no-any-return]


def review_if_due(org: Any, now: datetime) -> Review | None:
    return org.runtime.health_reviewer.review_if_due(now)  # type: ignore[no-any-return]


def total_runs(org: Any) -> int:
    return org.runtime.health_reviewer.total_runs()  # type: ignore[no-any-return]


def read_ledger(org: Any) -> dict[str, Any] | None:
    return org.runtime.health_reviewer.read_ledger()  # type: ignore[no-any-return]

