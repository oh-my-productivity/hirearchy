"""``TextualDashboardLauncher`` opens the queries of the organization it is told to show and hands them, with the interval, to the screen; and
``TextualScreenRunner`` is the screen: a Textual app on those queries."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.dashboard._app import DashApp
from orgmcp.dashboard._launcher import TextualDashboardLauncher, TextualScreenRunner
from orgmcp.dashboard.testing import MemoryQueriesOpener, RecordingScreens, fixed_queries
from orgmcp.kernel import OrgError

red = pytest.mark.xfail(strict=True, reason="red: D-dashboard")  # (until the app takes its queries: the next commit)

ROOT = Path("/memory/org")


def launcher() -> tuple[TextualDashboardLauncher, MemoryQueriesOpener, RecordingScreens]:
    opener, screens = MemoryQueriesOpener({ROOT}), RecordingScreens()
    return TextualDashboardLauncher(opener, screens), opener, screens


def test_the_queries_of_the_organization_are_shown_at_the_interval() -> None:
    made, opener, screens = launcher()
    made.run_dashboard(ROOT, 0.5)
    ((opened_root, queries),) = opener.opened
    assert opened_root == ROOT
    assert screens.runs == [(queries, 0.5)] and screens.runs[0][0] is queries


def test_the_default_interval_is_two_seconds() -> None:
    made, _, screens = launcher()
    made.run_dashboard(ROOT)
    assert [interval for _, interval in screens.runs] == [2.0]


def test_the_organization_is_opened_once_per_launch() -> None:
    made, opener, _ = launcher()
    made.run_dashboard(ROOT)
    made.run_dashboard(ROOT)
    assert len(opener.opened) == 2


def test_what_is_not_an_organization_never_reaches_the_screen() -> None:
    made, opener, screens = launcher()
    with pytest.raises(OrgError, match=r"not an organization \(no ORG.md\): /memory/elsewhere"):
        made.run_dashboard(Path("/memory/elsewhere"))
    assert opener.opened == [] and screens.runs == []


@red
def test_the_screen_runs_a_textual_app_on_the_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[DashApp] = []
    monkeypatch.setattr(DashApp, "run", lambda self, **_: ran.append(self))
    queries = fixed_queries()
    TextualScreenRunner().run(queries, 0.5)
    (app,) = ran
    assert app.data is queries and app.interval == 0.5


@red
def test_the_app_refreshes_at_least_five_times_a_second() -> None:
    assert DashApp(fixed_queries(), 0.01).interval == 0.2
    assert DashApp(fixed_queries(), 60).interval == 60.0
