# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import time

import pytest
from testkit.legacy.orgmcp.app import wire_attention
from testkit.legacy.orgmcp.core import ROOT

from orgmcp.daemon import SchedulerState
from orgmcp.daemon.testing import FakeSchedulerStatus
from orgmcp.progress import describe_progress
from orgmcp.progress._reporter import DerivedProgressReporter
from orgmcp.progress.testing import FixedSnapshots, SpyProgressView


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORGMCP_WORKSPACE_ROOTS", str(tmp_path))
    work = tmp_path / "cwd"
    (work / "<folder-with-your-files>").mkdir(parents=True)  # the documents example's input folder
    (work / "<folder-with-your-data>").mkdir()  # the analysis example's input folder
    monkeypatch.chdir(work)
    return work


@pytest.fixture
def task(org):
    return org.delegate(ROOT, "ceo", "Write the report", "goal", "criteria", budget=8)


def test_describe_progress_adds_the_scheduler_line_and_does_not_wait_without_one(org, task):
    t0 = time.monotonic()
    out = describe_progress(org, None, 600)  # no scheduler is running: it must answer at once
    assert time.monotonic() - t0 < 5
    assert out.startswith("Not waiting: no scheduler is running") and "working" in out
    assert out.splitlines()[-1].startswith("scheduler: stopped - open tasks do not move until it is started")


def test_describe_progress_waits_when_a_scheduler_runs(org, task):
    scheduler = FakeSchedulerStatus(SchedulerState("running", 1, "x"))
    view = SpyProgressView("lines")
    reporter = DerivedProgressReporter(view, FixedSnapshots(), scheduler, wire_attention.waiting_on_user_of(org.runtime), org.runtime.task_query)
    assert reporter.describe_progress(None, 30) == "lines\nscheduler: running (pid 1, since x)"
    assert view.kwargs == {"wait_seconds": 30}
