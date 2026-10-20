"""Every screen of the dashboard, as plain text, against the goldens in ``golden/``.

The goldens were taken from ``orgmcp/dashboard.py`` BEFORE it became a package (one file per screen: each view of the demo organization at 150x42, the tabs
of an agent, an open message, a trace, a service record, the events filtered / errors only / raw, the health with the check run, the help; the same
views at 80x24; the views of an organization that has only its root). That the package draws the same text is the proof that the move changed nothing a
user can see. The app is built the way the package builds it, ``DashApp(queries, interval)`` over the queries that the composition root makes.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest

from textual.app import App

from orgmcp.dashboard._app import DashApp as QueriedApp

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
