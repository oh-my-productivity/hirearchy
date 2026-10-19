"""``wire_dashboard``: the queries of one dashboard over a real organization, the launcher that shows them, and the two old ways in
(``DashApp(root, interval, now)`` and ``orgmcp.dashboard.run_dashboard(root, interval)``), which are thin over them."""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from types import ModuleType

import pytest

from orgmcp.app import Org
from orgmcp.dashboard import DashboardLauncher
from orgmcp.dashboard._ports import DashboardQueries
from orgmcp.dashboard.testing import FakeDashboardLauncher, RecordingScreens
from orgmcp.kernel import ROOT, OrgError

red = pytest.mark.xfail(strict=True, reason="red: D-dashboard")


def wire() -> ModuleType:
    return importlib.import_module("orgmcp.app.wire_dashboard")  # (does not exist yet)


@pytest.fixture
def team(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire(ROOT, "ceo", "Chief", "Lead.", can_hire=True)
    made.hire("ceo", "eng", "Engineer", "Build.")
    return made


@red
def test_the_queries_are_those_of_the_organization(team: Org) -> None:
    queries = wire().queries_of(team.root)
    assert isinstance(queries, DashboardQueries)
    snap = queries.snapshot()
    assert snap.org_name == "org" and [a for a in snap.order] == ["root", "ceo", "ceo/eng"]
    assert queries.feed is not None  # (made by the first snapshot)


@red
def test_the_time_shown_can_be_given(team: Org) -> None:
    from datetime import datetime, timezone

    then = datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc)
    assert wire().queries_of(team.root, lambda: then).snapshot().at == then


@red
def test_a_directory_that_is_not_an_organization_is_refused(tmp_path: Path) -> None:
    with pytest.raises(OrgError, match=r"not an organization \(no ORG.md\): "):
        wire().queries_of(tmp_path)


@red
def test_the_launcher_shows_the_queries_of_the_root_at_the_interval(team: Org) -> None:
    screens = RecordingScreens()
    launcher = wire().dashboard_launcher(screens)
    assert isinstance(launcher, DashboardLauncher)
    launcher.run_dashboard(team.root, 0.5)
    ((queries, interval),) = screens.runs
    assert interval == 0.5 and isinstance(queries, DashboardQueries) and "ceo/eng" in queries.snapshot().agents


@red
def test_the_launcher_refuses_a_directory_that_is_not_an_organization_before_the_screen(tmp_path: Path) -> None:
    screens = RecordingScreens()
    with pytest.raises(OrgError, match="not an organization"):
        wire().dashboard_launcher(screens).run_dashboard(tmp_path)
    assert screens.runs == []


@red
def test_run_dashboard_is_the_launcher_of_the_wiring(team: Org, monkeypatch: pytest.MonkeyPatch) -> None:
    from orgmcp.dashboard import run_dashboard

    fake = FakeDashboardLauncher({team.root})
    monkeypatch.setattr(wire(), "dashboard_launcher", lambda screens=None: fake)
    run_dashboard(str(team.root), 0.7)
    run_dashboard(team.root)
    assert fake.launched == [(team.root, 0.7), (team.root, 2.0)]


def test_run_dashboard_keeps_the_signature_the_command_line_calls() -> None:
    from orgmcp.dashboard import run_dashboard

    parameters = inspect.signature(run_dashboard).parameters
    assert list(parameters) == ["root", "interval"] and parameters["interval"].default == 2.0
    assert inspect.signature(run_dashboard).return_annotation in (None, "None")


def test_the_old_constructor_of_the_app_asks_the_wiring_for_its_queries(team: Org) -> None:
    from orgmcp.dashboard import DashApp

    app = DashApp(team.root, interval=60)
    assert isinstance(app.data, DashboardQueries) and "ceo" in app.data.snapshot().agents and app.interval == 60.0


@red
def test_the_stylesheet_travels_with_the_package() -> None:
    from orgmcp.dashboard._app import DashApp

    assert Path(str(DashApp.CSS_PATH)).is_file() and Path(str(DashApp.CSS_PATH)).name == "dashboard.tcss"
