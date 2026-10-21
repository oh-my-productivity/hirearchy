"""``ScriptedHealthReviewer``: the stand-in of the reviewer for the consumers that decide *when* to review or print the result."""

from __future__ import annotations

from datetime import datetime, timezone

from hirearchy.review import HealthReviewer, Note, Review
from hirearchy.review.testing import ScriptedHealthReviewer

AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
DONE = Review(at=AT, runs=3, flagged=1, notes=[Note("root", "t", "b")])


def test_it_is_a_reviewer() -> None:
    assert isinstance(ScriptedHealthReviewer(DONE), HealthReviewer)


def test_it_answers_with_the_reviews_it_was_given_and_remembers_the_calls() -> None:
    fake = ScriptedHealthReviewer(DONE, due=None, runs=9, ledger={"at": "x", "runs": 1, "notified": {}})
    assert fake.review(AT, dry_run=True) is DONE and fake.review() is DONE
    assert fake.review_if_due(AT) is None and fake.total_runs() == 9 and fake.read_ledger() == {"at": "x", "runs": 1, "notified": {}}
    assert fake.calls == [("review", AT, True), ("review", None, False), ("review_if_due", AT, False), ("total_runs", None, False), ("read_ledger", None, False)]


def test_a_review_that_is_due_is_the_one_given() -> None:
    assert ScriptedHealthReviewer(DONE, due=DONE).review_if_due(AT) is DONE
