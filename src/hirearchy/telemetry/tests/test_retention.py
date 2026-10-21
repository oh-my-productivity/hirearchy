# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import os
import shutil
import sys
from datetime import datetime, timedelta, timezone

import pytest
import testkit
from testkit import telemetry_world as telemetry
from testkit.health_world import Scheduler
from testkit.reach.hirearchy.core import join_frontmatter, split_frontmatter

FAKE = str(testkit.FAKE_AGENT)
SILENT = {"echo": lambda _: None}


# ---------------------------------------------------------------------------------------------------- helpers
@pytest.fixture
def org(org):
    """The shared org, with the events of its construction (hires) forgotten: tests see only their own."""
    shutil.rmtree(org.root / ".runtime" / "events", ignore_errors=True)
    telemetry.reset()
    return org


def configure(org, **changes):
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


def fake_runner(mode="work"):
    def build(org, addr, prompt):
        env = {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": mode}
        return [sys.executable, FAKE], org.dir(addr), env

    return build


# --------------------------------------------------------------------------------- retention and git hygiene
def test_prune_removes_only_old_day_directories(org):
    base = org.root / ".runtime" / "events"
    today = datetime(2026, 10, 18, tzinfo=timezone.utc)
    for offset in (0, 1, 29, 30, 31, 90):
        d = base / (today - timedelta(days=offset)).strftime("%Y-%m-%d")
        d.mkdir(parents=True)
        (d / "mcp-1-1.jsonl").write_text("{}\n")
    (base / "notes").mkdir()
    removed = telemetry.prune(org.root, 30, today=today)
    assert removed == ["2026-07-20", "2026-09-17"]
    assert sorted(p.name for p in base.iterdir()) == ["2026-09-18", "2026-09-19", "2026-10-17", "2026-10-18", "notes"]
    assert telemetry.prune(org.root, 30, today=today) == []
    assert telemetry.prune(org.root / "missing", 30) == []


def test_keep_days_is_configurable(org):
    configure(org, events_keep_days=3)
    base = org.root / ".runtime" / "events"
    old = base / (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
    old.mkdir(parents=True)
    Scheduler(org, fake_runner("idle"), **SILENT).tick()
    assert not old.exists()
