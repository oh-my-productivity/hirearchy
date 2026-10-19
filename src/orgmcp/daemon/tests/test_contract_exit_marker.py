"""Contract of ``ExitMarker``: why the last scheduler exited by itself, kept in a file."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.daemon import ExitMarker
from orgmcp.daemon.testing import IMPLEMENTATIONS, MarkerWorld

from ._support import build, worlds


@pytest.fixture(params=worlds(IMPLEMENTATIONS[ExitMarker]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> MarkerWorld:
    world = build(request, tmp_path, MarkerWorld)
    assert isinstance(world.marker, ExitMarker)
    return world


def test_without_a_marker_there_is_no_reason(w: MarkerWorld) -> None:
    assert w.raw() is None and w.marker.read() == ""


def test_the_reason_is_kept_as_one_line_and_read_back(w: MarkerWorld) -> None:
    w.marker.write("finished: no open tasks")
    assert w.raw() == "finished: no open tasks\n"
    assert w.marker.read() == "finished: no open tasks"


def test_a_later_reason_replaces_the_earlier_one(w: MarkerWorld) -> None:
    w.marker.write("first")
    w.marker.write("second")
    assert w.raw() == "second\n" and w.marker.read() == "second"


def test_clear_forgets_the_reason(w: MarkerWorld) -> None:
    w.marker.write("finished: no open tasks")
    w.marker.clear()
    assert w.raw() is None and w.marker.read() == ""


def test_clear_without_a_marker_is_harmless(w: MarkerWorld) -> None:
    w.marker.clear()
    w.marker.clear()
    assert w.raw() is None


@pytest.mark.parametrize(("text", "reason"), [("why\n", "why"), ("  why  \n\n", "why"), ("\n", ""), ("", ""), ("  \n ", ""), ("a\nb\n", "a\nb")])
def test_the_reason_read_is_stripped(w: MarkerWorld, text: str, reason: str) -> None:
    w.put(text)
    assert w.marker.read() == reason
