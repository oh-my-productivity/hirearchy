# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import json
import os
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest
import testkit
from testkit.legacy.orgmcp.app import wiring
from testkit.scheduler_loop import loop_over

FAKE = str(testkit.FAKE_AGENT)
SILENT = {"echo": lambda _: None}


# ---------------------------------------------------------------------------------------------------- helpers
@pytest.fixture
def org(org):
    """The shared org, with the events of its construction (hires) forgotten: tests see only their own."""
    shutil.rmtree(org.root / ".runtime" / "events", ignore_errors=True)
    wiring.process_resources().reset()  # forget the open event files and counters of the process
    return org


def event_files(org):
    return sorted((org.root / ".runtime" / "events").glob("*/*.jsonl"))


def read_events(org, kind=None):
    """Every event of the org, merged by time (the way a reader would)."""
    out = []
    for f in event_files(org):
        for line in f.read_text(encoding="utf-8").splitlines():
            out.append(json.loads(line))  # every line is a valid JSON object
    out.sort(key=lambda e: (e["ts"], e["seq"]))
    return [e for e in out if kind is None or e["kind"] == kind]


def fake_runner(mode="work"):
    def build(org, addr, prompt):
        env = {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": mode}
        return [sys.executable, FAKE], org.dir(addr), env

    return build


class Clock:
    def __init__(self):
        self.offset = 0.0

    def __call__(self):
        return time.time() + self.offset

    def advance(self, seconds):
        self.offset += seconds


def test_the_scheduler_prunes_once_a_day_and_says_so(org):
    base = org.root / ".runtime" / "events"
    old = base / (datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%d")
    old.mkdir(parents=True)
    (old / "mcp-1-1.jsonl").write_text("{}\n")
    clock = Clock()
    sched = loop_over(org, fake_runner("idle"), clock=clock, **SILENT)
    sched.tick()
    assert not old.exists()
    (prune,) = read_events(org, "prune")
    assert prune["removed_days"] == [old.name] and prune["proc"] == "scheduler" and prune["actor"] == "runtime"
    again = base / (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
    again.mkdir()
    sched.tick()
    assert again.exists()  # not within a day
    clock.advance(86400 + 1)
    sched.tick()
    assert not again.exists()
