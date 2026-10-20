# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import pytest
from testkit.dash_fixtures import DEMO_NOW, demo_org, snapshot_files
from testkit.legacy.orgmcp import dashboard_data as dd
from testkit.legacy.orgmcp.scheduler import SchedulerState
from testkit.scheduler import scheduler_is

from orgmcp.cli import main


@pytest.fixture
def sched_up(monkeypatch):
    up = lambda o: SchedulerState("running", 7000, "2026-10-18 10:00:00Z")  # noqa: E731
    scheduler_is(monkeypatch, up(None))


@pytest.fixture
def demo(tmp_path, sched_up):
    ns = demo_org(tmp_path)
    ns.data = dd.DashData(ns.org.root, now=lambda: DEMO_NOW)
    return ns


# ------------------------------------------------------------------------------------------ read-only
def test_the_data_layer_and_once_write_nothing(demo, capsys):
    before = snapshot_files(demo.org.root)
    data = dd.DashData(demo.org.root, now=lambda: DEMO_NOW)
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
    dd.render_once(data)
    main(["--root", str(demo.org.root), "dash", "--once"])
    out = capsys.readouterr().out
    assert "AGENTS" in out and "ceo" in out
    assert snapshot_files(demo.org.root) == before


def test_dash_on_something_that_is_not_an_org(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main(["--root", str(tmp_path), "dash", "--once"])
    assert "not an organization" in capsys.readouterr().err
    assert not (tmp_path / ".runtime").exists()
