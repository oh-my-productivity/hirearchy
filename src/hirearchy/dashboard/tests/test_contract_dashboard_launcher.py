"""Contract of ``DashboardLauncher``: it puts the dashboard of the organization it is given on the screen, refreshing at the interval it is told, and refuses
what is not an organization before the screen is taken. Over the Textual launcher (on screens that record) and over the recording launcher."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from hirearchy.dashboard import DashboardLauncher
from hirearchy.dashboard.testing import IMPLEMENTATIONS, LauncherWorld
from hirearchy.kernel import OrgError



@pytest.fixture(params=IMPLEMENTATIONS[DashboardLauncher], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> LauncherWorld:
    made = cast(LauncherWorld, request.param(tmp_path))
    assert isinstance(made.launcher, DashboardLauncher)
    return made


def test_the_default_interval_is_two_seconds(w: LauncherWorld) -> None:
    w.launcher.run_dashboard(w.root)
    assert w.shown() == [(w.root, 2.0)]


def test_the_interval_is_the_one_asked_for(w: LauncherWorld) -> None:
    w.launcher.run_dashboard(w.root, 0.5)
    w.launcher.run_dashboard(w.root, interval=30.0)
    assert w.shown() == [(w.root, 0.5), (w.root, 30.0)]


def test_nothing_is_shown_for_what_is_not_an_organization(w: LauncherWorld) -> None:
    with pytest.raises(OrgError, match="not an organization"):
        w.launcher.run_dashboard(w.elsewhere)
    assert w.shown() == []


def test_a_refusal_does_not_stop_the_next_launch(w: LauncherWorld) -> None:
    with pytest.raises(OrgError):
        w.launcher.run_dashboard(w.elsewhere)
    w.launcher.run_dashboard(w.root, 1.0)
    assert w.shown() == [(w.root, 1.0)]
