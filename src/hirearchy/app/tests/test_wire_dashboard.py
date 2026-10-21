"""``wire_dashboard``: the queries of one dashboard over a real organization, and the launcher that shows them."""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from hirearchy.app import Org
from hirearchy.dashboard import DashboardLauncher
from hirearchy.dashboard._ports import DashboardQueries
from hirearchy.dashboard.testing import RecordingScreens
from hirearchy.kernel import ROOT, OrgError



def wire() -> ModuleType:
    return importlib.import_module("hirearchy.app.wire_dashboard")  # (does not exist yet)


@pytest.fixture
def team(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire(ROOT, "ceo", "Chief", "Lead.", can_hire=True)
    made.hire("ceo", "eng", "Engineer", "Build.")
    return made


def test_the_queries_are_those_of_the_organization(team: Org) -> None:
    queries = wire().queries_of(team.root)
    assert isinstance(queries, DashboardQueries)
    snap = queries.snapshot()
    assert snap.org_name == "org" and [a for a in snap.order] == ["root", "ceo", "ceo/eng"]
    assert queries.feed is not None  # (made by the first snapshot)


def test_the_time_shown_can_be_given(team: Org) -> None:
    from datetime import datetime, timezone

    then = datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc)
    assert wire().queries_of(team.root, lambda: then).snapshot().at == then


def test_a_directory_that_is_not_an_organization_is_refused(tmp_path: Path) -> None:
    with pytest.raises(OrgError, match=r"not an organization \(no ORG.md\): "):
        wire().queries_of(tmp_path)


def test_the_launcher_shows_the_queries_of_the_root_at_the_interval(team: Org) -> None:
    screens = RecordingScreens()
    launcher = wire().dashboard_launcher(screens)
    assert isinstance(launcher, DashboardLauncher)
    launcher.run_dashboard(team.root, 0.5)
    ((queries, interval),) = screens.runs
    assert interval == 0.5 and isinstance(queries, DashboardQueries) and "ceo/eng" in queries.snapshot().agents


def test_the_launcher_refuses_a_directory_that_is_not_an_organization_before_the_screen(tmp_path: Path) -> None:
    screens = RecordingScreens()
    with pytest.raises(OrgError, match="not an organization"):
        wire().dashboard_launcher(screens).run_dashboard(tmp_path)
    assert screens.runs == []


def test_the_stylesheet_travels_with_the_package() -> None:
    from hirearchy.dashboard._app import DashApp

    assert Path(str(DashApp.CSS_PATH)).is_file() and Path(str(DashApp.CSS_PATH)).name == "dashboard.tcss"


def test_loading_the_wiring_does_not_load_the_dashboard_or_textual() -> None:
    """Every runtime loads every ``wire_*`` module; the terminal framework is for ``hirearchy dash`` only (``Org(root)`` and ``status`` must not pay for it)."""
    probe = (
        "import sys\n"
        "from hirearchy.app import wiring\n"
        "wiring.providers()\n"
        "assert 'hirearchy.app.wire_dashboard' in sys.modules\n"
        "loaded = sorted(m for m in sys.modules if m == 'textual' or m.startswith(('textual.', 'hirearchy.dashboard')))\n"
        "assert not loaded, loaded\n"
    )
    done = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
