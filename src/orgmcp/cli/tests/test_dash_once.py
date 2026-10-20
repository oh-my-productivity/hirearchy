# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.cli_world import clock_is, main
from testkit.dash_fixtures import DEMO_NOW, demo_org, snapshot_files
from testkit.reach.orgmcp.app.wire_dashdata import dashboard_runtime
from testkit.scheduler import scheduler_is

from orgmcp.daemon import SchedulerState
from orgmcp.kernel.testing import FakeClock


@pytest.fixture
def sched_up(process_overrides):
    up = lambda o: SchedulerState("running", 7000, "2026-10-18 10:00:00Z")  # noqa: E731
    scheduler_is(process_overrides, up(None))


class DashData:
    """What ``dashboard_data.DashData(root, now=...)`` answered, over the queries of the runtime of the dashboard."""

    def __init__(self, root, now):
        rt = dashboard_runtime(root, now=now)
        self.snapshot = rt.snapshot_query.snapshot
        self.agent_detail = rt.agent_detail_query.agent_detail
        self.requests, self.trace_text, self.request_line = rt.request_query.requests, rt.request_query.trace_text, rt.request_query.request_line
        self.services, self.service_detail = rt.service_query.services, rt.service_query.service_detail
        self.health, self.run_check = rt.health_query.health, rt.health_query.run_check
        self.render_once = rt.snapshot_renderer.render_once


def render_once(data):
    """``dashboard_data.render_once(data)``: the text of ``dash --once``."""
    return data.render_once()


@pytest.fixture
def demo(tmp_path, sched_up, process_overrides):
    ns = demo_org(tmp_path)
    clock_is(process_overrides, FakeClock(DEMO_NOW))  # after the demo is built (under its own clock): every runtime opened from here on is at DEMO_NOW
    ns.data = DashData(ns.org.root, now=lambda: DEMO_NOW)
    return ns


# ------------------------------------------------------------------------------------------ read-only
def test_the_data_layer_and_once_write_nothing(demo, capsys):
    before = snapshot_files(demo.org.root)
    data = DashData(demo.org.root, now=lambda: DEMO_NOW)
    snap = data.snapshot()
    for a in snap.order:
        data.agent_detail(a, snap)
    data.requests(snap)
    data.services(snap)
    data.service_detail("research", "market-brief")
    data.health(snap)
    data.run_check()
    data.trace_text(demo.report_task.id)
    data.request_line(demo.report_task.id)
    render_once(data)
    main(["--root", str(demo.org.root), "dash", "--once"])
    out = capsys.readouterr().out
    assert "AGENTS" in out and "ceo" in out
    assert snapshot_files(demo.org.root) == before


def test_dash_on_something_that_is_not_an_org(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main(["--root", str(tmp_path), "dash", "--once"])
    assert "not an organization" in capsys.readouterr().err
    assert not (tmp_path / ".runtime").exists()
