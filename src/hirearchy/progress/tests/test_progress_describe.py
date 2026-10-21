# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import time

import pytest
from testkit.reach.hirearchy.core import ROOT
from testkit.progress_world import describe_progress

from hirearchy.daemon import SchedulerState
from hirearchy.daemon.testing import FakeSchedulerStatus
from hirearchy.progress._reporter import DerivedProgressReporter
from hirearchy.progress.testing import FixedSnapshots, SpyProgressView


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))
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
    reporter = DerivedProgressReporter(view, FixedSnapshots(), scheduler, org.runtime.waiting_on_user, org.runtime.task_query)
    assert reporter.describe_progress(None, 30) == "lines\nscheduler: running (pid 1, since x)"
    assert view.kwargs == {"wait_seconds": 30}
