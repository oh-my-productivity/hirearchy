"""``DashApp`` built on queries that are only data (``dashboard.testing.fixed_queries``) shows every screen and touches no file.

The organization the queries describe is at ``/memory/org``, which does not exist; the working directory is an empty temporary one. An audit hook notes
every attempt to open, list or change anything below ``/memory``, and the directory must still be empty at the end: whatever the app shows, it was
told by the queries it was given, not read from disk.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Awaitable, Callable, Iterator
from pathlib import Path

import pytest
from textual.pilot import Pilot
from textual.widgets import Static, TabbedContent
from textual.widgets.tree import TreeNode

from orgmcp.dashboard._app import DashApp
from orgmcp.dashboard._widgets import NavTable, TextPane, TextScreen
from orgmcp.dashboard._ports import DashboardQueries
from orgmcp.dashboard.testing import ORG_ROOT, detail, fixed_queries, request_row
from orgmcp.dashdata import Section, ServiceRow
from orgmcp.dashdata.testing import MemoryEventFeed
from orgmcp.reflection import Stats

TOUCHING = {"open", "os.listdir", "os.scandir", "os.mkdir", "os.rename", "os.remove", "os.rmdir", "os.chmod", "shutil.copyfile"}
touched: list[str] = []
watching: list[bool] = []
installed: list[bool] = []


def hook(event: str, args: tuple[object, ...]) -> None:
    if watching and event in TOUCHING and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = os.fsdecode(args[0])
        if path.startswith("/memory"):
            touched.append(f"{event} {path}")


@pytest.fixture
def untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    if not installed:
        sys.addaudithook(hook)  # (a hook cannot be removed: it only looks while ``watching``)
        installed.append(True)
    monkeypatch.chdir(tmp_path)
    touched.clear()
    watching.append(True)
    yield tmp_path
    watching.clear()
    assert touched == [] and os.listdir(tmp_path) == []


def service_row() -> ServiceRow:
    return ServiceRow("ops", "brief", 1, 2, False, Stats(requests=3, done=2, open=1), "initial playbook", "A brief.")


Scenario = Callable[[DashApp, Pilot[None]], Awaitable[None]]


def run(fn: Scenario, queries: DashboardQueries | None = None, size: tuple[int, int] = (110, 34)) -> None:
    async def go() -> None:
        app = DashApp(queries or fixed_queries(), interval=3600)
        async with app.run_test(size=size) as pilot:
            await app.settle(pilot)
            await fn(app, pilot)

    asyncio.run(go())


def text(app: DashApp, selector: str) -> str:
    return str(app.query_one(selector, TextPane).text_now)


def test_the_header_and_the_tree_show_the_snapshot(untouched: Path) -> None:
    async def fn(app: DashApp, pilot: Pilot[None]) -> None:
        title = str(app.query_one("#header-title", Static).render())
        counts = str(app.query_one("#header-counts", Static).render())
        assert "memo" in title and "10:06:40Z" in title and "refresh 3600s" in title
        assert "scheduler running pid 4242" in counts and "running 1/2" in counts and "queued 1" in counts and "waiting on you 1" in counts
        nodes: dict[str, TreeNode[str]] = getattr(app.query_one("#agent-tree"), "nodes")
        labels = {addr: str(node.label) for addr, node in nodes.items()}
        assert labels["root"].startswith("★ root (you)") and "needs you: 1" in labels["root"]
        assert labels["ops"].startswith("▶ ops  running 1m12s") and labels["ops/eng"].startswith("◔ eng  queued: starts on the next tick")
        assert labels["scribe"].startswith("○ scribe  idle")

    run(fn, size=(110, 34))
    assert os.listdir(untouched) == []


def test_the_details_of_the_selected_agent_come_from_the_detail_query(untouched: Path) -> None:
    queries = fixed_queries(details={"root": detail("root", "You (root)"), "ops": detail("ops", "state    ▶ running 1m12s", "elapsed 1m12s")})

    async def fn(app: DashApp, pilot: Pilot[None]) -> None:
        assert "You (root)" in text(app, "#pane-overview")
        await pilot.press("down")
        await app.settle(pilot)
        assert app.selected == "ops" and "state    ▶ running 1m12s" in text(app, "#pane-overview")
        await pilot.press("]", "]", "]", "]", "]")
        await app.settle(pilot)
        assert app.query_one("#agent-tabs", TabbedContent).active == "tab-charter"  # (the details of the others are filled when their tab is opened)
        assert text(app, "#pane-charter") == "role: ops"

    run(fn, queries)


def test_the_workflows_screen_lists_the_requests_and_opens_a_trace(untouched: Path) -> None:
    queries = fixed_queries(requests=[request_row("t-1", "Write the report")], traces={"t-1": "trace t-1: nothing happened yet"})

    async def fn(app: DashApp, pilot: Pilot[None]) -> None:
        await pilot.press("2")
        await app.settle(pilot)
        (row,) = [[c.plain for c in app.query_one("#flows-table", NavTable).get_row(k)] for k in app.query_one("#flows-table", NavTable).rows]
        assert row[0] == "working" and row[1] == "Write the report" and row[2] == "ops" and row[3] == "1/4"
        await pilot.press("enter")
        await app.settle(pilot)
        assert "trace t-1: nothing happened yet" in text(app, "#flows-detail")
        await pilot.press("escape")
        assert app.flow_open is None

    run(fn, queries)


def test_the_services_screen_lists_the_services_and_opens_one(untouched: Path) -> None:
    queries = fixed_queries(services=[service_row()], service_details={("ops", "brief"): [Section("brief (owner ops)", ["Cases (3)"])]})

    async def fn(app: DashApp, pilot: Pilot[None]) -> None:
        await pilot.press("3")
        await app.settle(pilot)
        (row,) = [[c.plain for c in app.query_one("#services-table", NavTable).get_row(k)] for k in app.query_one("#services-table", NavTable).rows]
        assert row[0] == "brief" and row[1] == "ops" and row[2] == "c1 p2" and row[3] == "3" and row[4] == "2/0/1"
        await pilot.press("enter")
        await app.settle(pilot)
        assert "Cases (3)" in text(app, "#services-detail")

    run(fn, queries)


def test_the_events_screen_shows_the_feed_the_state_keeps(untouched: Path) -> None:
    feed = MemoryEventFeed([{"kind": "run.start", "agent": "ops"}, {"kind": "tool.call", "agent": "ops", "ok": False}])

    async def fn(app: DashApp, pilot: Pilot[None]) -> None:
        await pilot.press("4")
        await app.settle(pilot)
        assert text(app, "#events-body").splitlines() == ["run.start", "tool.call"]
        assert "2 of 2 event(s) in memory" in str(app.query_one("#events-bar", Static).render())

    run(fn, fixed_queries(feed=feed))


def test_the_health_screen_and_the_check_on_demand(untouched: Path) -> None:
    async def fn(app: DashApp, pilot: Pilot[None]) -> None:
        await pilot.press("5")
        await app.settle(pilot)
        body = text(app, "#health-body")
        assert "scheduler: running pid 4242" in body and "scribe" in body and "!out_of_budget: no budget left" in body and "not run yet - press c" in body
        await pilot.press("c")
        for _ in range(100):
            await app.settle(pilot)
            if "checked at" in text(app, "#health-body"):
                break
            await asyncio.sleep(0.01)
        assert "checked at 10:06:40Z\n(a) PASS messages intact" in text(app, "#health-body")

    run(fn, fixed_queries())


def test_a_message_overlay_and_the_help_open_and_close(untouched: Path) -> None:
    async def fn(app: DashApp, pilot: Pilot[None]) -> None:
        await pilot.press("question_mark")
        assert isinstance(app.screen, TextScreen)
        await pilot.press("escape")
        assert not isinstance(app.screen, TextScreen)

    run(fn, fixed_queries())


def test_the_organization_the_app_describes_is_not_on_disk() -> None:
    app = DashApp(fixed_queries(), interval=3600)
    assert app.data.snapshot().root == str(ORG_ROOT) and not ORG_ROOT.exists()
