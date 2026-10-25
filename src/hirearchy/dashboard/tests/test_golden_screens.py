"""Every screen of the dashboard, as plain text, against the goldens in ``golden/``.

The goldens were taken from ``hirearchy/dashboard.py`` BEFORE it became a package (one file per screen: each view of the demo organization at 150x42, the tabs
of an agent, an open message, a trace, a service record, the events filtered / errors only / raw, the health with the check run, the help; the same
views at 80x24; the views of an organization that has only its root). That the package draws the same text is the proof that the move changed nothing a
user can see. The app is built the way the package builds it, ``DashApp(queries, interval)`` over the queries that the composition root makes.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest

from rich.text import Text
from textual.app import App, ComposeResult

from hirearchy.dashboard._app import DashApp as QueriedApp
from hirearchy.dashboard._widgets import NavTable

from . import _screens, _worlds

NAMES = sorted(path.stem for path in _screens.GOLDEN.glob("*.txt"))


def given_queries(root: Path) -> App[None]:
    return QueriedApp(_worlds.queries_of(root, _worlds.shown), interval=3600)


@pytest.fixture(scope="module", params=[given_queries], ids=lambda made: made.__name__)
def screens(request: pytest.FixtureRequest) -> Iterator[dict[str, str]]:
    with contextlib.ExitStack() as stack, pytest.MonkeyPatch.context() as patch, _worlds.scratch() as base:
        patch.setenv("HOME", str(base))

        def process_overrides(overrides: Mapping[type, object]) -> object:
            return stack.enter_context(_worlds.overriding(overrides))

        demo = _worlds.demo(process_overrides, base)
        taken = _screens.demo_screens(request.param, demo.org.root)
        empty = _worlds.empty(process_overrides, base)
        taken.update(_screens.empty_screens(request.param, empty.root))
        yield taken


def test_the_screens_taken_are_the_goldens_there_are(screens: dict[str, str]) -> None:
    assert sorted(screens) == NAMES
    assert len(NAMES) == 34


@pytest.mark.parametrize("name", NAMES)
def test_a_screen_is_what_its_golden_says(screens: dict[str, str], name: str) -> None:
    assert screens[name] == _screens.golden_path(name).read_text(encoding="utf-8")


class TableHost(App[None]):
    """An app that is only a table, as tall as the screen like the tables of the dashboard (``dashboard.tcss``)."""

    CSS = "NavTable { height: 1fr; }"

    def compose(self) -> ComposeResult:
        yield NavTable(id="table")


def test_a_frame_drawn_before_the_table_has_measured_its_columns_does_not_outlive_the_measure() -> None:
    """``DataTable`` measures its columns when it is idle, and keeps what it drew under a key that the measure does not change. A screen update that lands
    between the rows being added and the measure (on a loaded machine it does, now and then) drew the cells cut to the width of their labels, and the
    table kept showing them: the narrow-2-workflows golden failed one capture in about a hundred. The table drops what it drew once its size says that
    the columns changed."""
    columns = [("state", "state"), ("title", "request")]
    rows = [("a", [Text("working"), Text("Brief: heat pumps")])]

    async def go() -> tuple[str, str]:
        app = TableHost()
        async with app.run_test(size=(60, 8)) as pilot:
            table = app.query_one(NavTable)
            table.sync(columns, [])
            await pilot.pause()  # (the columns are measured with nothing in them: the width of their labels)
            drawn: list[str] = []
            table.sync(columns, rows)
            table.call_later(lambda: drawn.append(_screens.plain(app)))  # (queued behind the table's own wake-up: it runs before the table is idle)
            await pilot.pause()
            return drawn[0], _screens.plain(app)

    early, late = asyncio.run(go())
    assert "worki " in early and "working" not in early, "the premise: a frame drawn before the measure has the cells cut"
    assert "working  Brief: heat pumps" in late
