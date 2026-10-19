"""``wire_review``: the runtime has the reviewer, built from the ports of the runtime; and the scheduler asks the reviewer of the runtime in force when
a review may be due."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from pathlib import Path

from orgmcp.app import Org, wiring
from orgmcp.review import HealthReviewer, Note, Review
from orgmcp.review._reviewer import LedgerHealthReviewer
from orgmcp.review.testing import ScriptedHealthReviewer
from orgmcp.scheduler import Scheduler
from orgmcp.templates import Notices
from orgmcp.templates.testing import RecordingNotices

AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_the_runtime_has_the_reviewer(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.health_reviewer, LedgerHealthReviewer) and isinstance(runtime.health_reviewer, HealthReviewer)
    assert runtime.health_reviewer is runtime.health_reviewer


def test_building_the_reviewer_does_no_io(tmp_path: Path) -> None:
    assert wiring.open_runtime(tmp_path).health_reviewer is not None
    assert list(tmp_path.iterdir()) == []


def test_an_override_replaces_the_port(tmp_path: Path) -> None:
    fake = ScriptedHealthReviewer(Review(at=AT, runs=0, flagged=0))
    assert wiring.open_runtime(tmp_path, {HealthReviewer: fake}).health_reviewer is fake


def test_the_notes_are_worded_by_the_notices_of_the_runtime(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "m")
    org.hire("root", "ceo", "Chief", "Run it.", can_hire=True)
    org.hire("ceo", "eng", "Engineer", "Build.")
    notices = RecordingNotices()
    org.runtime = wiring.open_runtime(org.root, {Notices: notices})
    org.runtime.health_reviewer.review(AT.replace(year=2030), dry_run=True)  # years later: everybody is idle
    assert any(name == "review_root" for name, _ in notices.calls)


def test_the_scheduler_asks_the_reviewer_of_the_runtime_in_force(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "m")
    done = Review(at=AT, runs=0, flagged=2, notes=[Note("ceo", "t", "b"), Note("root", "t", "b")])
    fake = ScriptedHealthReviewer(done, due=done)
    seen: list[str] = []
    sched = Scheduler(org, echo=seen.append, clock=lambda: AT.timestamp())
    org.runtime = dataclasses.replace(org.runtime, health_reviewer=fake)  # tests replace the runtime under a running scheduler
    sched._check_review()
    assert fake.calls == [("review_if_due", AT, False)] and seen == ["health review: 2 flagged, told ceo, root"]
