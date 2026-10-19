"""Every screen of the dashboard, as plain text, against the goldens in ``golden/``.

The goldens were taken from ``orgmcp/dashboard.py`` BEFORE it became a package (one file per screen: each view of the demo organization at 150x42, the tabs
of an agent, an open message, a trace, a service record, the events filtered / errors only / raw, the health with the check run, the help; the same
views at 80x24; the views of an organization that has only its root). That the package draws the same text is the proof that the move changed nothing a
user can see. The app is built the way ``orgmcp dash`` builds it and the way a test built it before: ``DashApp(root, interval, now)``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from orgmcp.dashboard import DashApp

from . import _screens, _worlds

NAMES = sorted(path.stem for path in _screens.GOLDEN.glob("*.txt"))


@pytest.fixture(scope="module")
def screens() -> Iterator[dict[str, str]]:
    with pytest.MonkeyPatch.context() as patch, _worlds.scratch() as base:
        patch.setenv("HOME", str(base))
        demo = _worlds.demo(patch, base)
        now = _worlds.shown
        taken = _screens.demo_screens(lambda root: DashApp(root, interval=3600, now=now), demo.org.root)
        empty = _worlds.empty(patch, base)
        taken.update(_screens.empty_screens(lambda root: DashApp(root, interval=3600, now=now), empty.root))
        yield taken


def test_the_screens_taken_are_the_goldens_there_are(screens: dict[str, str]) -> None:
    assert sorted(screens) == NAMES
    assert len(NAMES) == 34


@pytest.mark.parametrize("name", NAMES)
def test_a_screen_is_what_its_golden_says(screens: dict[str, str], name: str) -> None:
    assert screens[name] == _screens.golden_path(name).read_text(encoding="utf-8")
