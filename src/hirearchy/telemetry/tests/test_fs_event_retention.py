"""``FsEventRetention``: the retention rules on a real events directory, and its promise never to raise."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from hirearchy.eventlog import EVENTS_REL
from hirearchy.kernel import OrgPaths
from hirearchy.kernel.testing import FakeClock
from hirearchy.telemetry._pool import EventWriterPool
from hirearchy.telemetry._retention import FsEventRetention
from hirearchy.telemetry.testing import sink_kit


def test_the_cutoff_is_the_day_keep_days_before_today_and_that_day_stays(tmp_path: Path) -> None:
    retention = FsEventRetention(OrgPaths(tmp_path), FakeClock(), EventWriterPool(FakeClock()))
    today = datetime(2026, 10, 18, 23, 59, tzinfo=timezone.utc)
    base = tmp_path / EVENTS_REL
    for offset in (29, 30, 31):
        d = base / (today - timedelta(days=offset)).strftime("%Y-%m-%d")
        d.mkdir(parents=True)
        (d / "mcp-1-1.jsonl").write_text("{}\n")
    assert retention.prune(30, today=today) == ["2026-09-17"]
    assert sorted(p.name for p in base.iterdir()) == ["2026-09-18", "2026-09-19"]


def test_a_file_named_like_a_day_is_not_a_day_directory(tmp_path: Path) -> None:
    base = tmp_path / EVENTS_REL
    base.mkdir(parents=True)
    (base / "2020-01-01").write_text("not a directory")
    retention = FsEventRetention(OrgPaths(tmp_path), FakeClock(), EventWriterPool(FakeClock()))
    assert retention.prune(30) == [] and (base / "2020-01-01").exists()


def test_the_default_for_today_is_the_clock(tmp_path: Path) -> None:
    kit = sink_kit(tmp_path)
    base = tmp_path / EVENTS_REL
    (base / "2026-09-17").mkdir(parents=True)
    (base / "2026-09-18").mkdir()
    retention = FsEventRetention(OrgPaths(tmp_path), kit.clock, kit.pool)  # the clock says 2026-10-18
    assert retention.prune(30) == ["2026-09-17"]


def test_a_failure_is_swallowed_counted_and_the_removed_so_far_are_returned(tmp_path: Path) -> None:
    class Broken(FakeClock):
        def now(self) -> datetime:
            raise RuntimeError("the clock is broken")

    pool = EventWriterPool(FakeClock())
    retention = FsEventRetention(OrgPaths(tmp_path), Broken(), pool)
    assert retention.prune(30) == [] and pool.dropped() == 1
