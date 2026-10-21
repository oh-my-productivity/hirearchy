"""The organizations the screens are taken of, from ``tests/testkit/dash_worlds.py`` (the demo organization of ``dash_fixtures`` and an empty one).

The fixtures build them with the ``Org`` facade, which a package may not import (not even in its tests), so they are looked up by name; what comes
back is typed here. Until the fixtures move into ``tests/testkit`` (E1-e) this is the one place that knows where they are.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from datetime import datetime
from pathlib import Path
from typing import Protocol, cast

import pytest

from hirearchy.dashboard._ports import DashboardQueries


class Organization(Protocol):
    """What the screens need of an organization: where it is."""

    root: Path


class DemoWorld(Protocol):
    """The demo organization with what the tests ask of it."""

    org: Organization


def _fixtures() -> object:
    return importlib.import_module("testkit.dash_worlds")


def shown() -> datetime:
    """The time the demo organization is shown at (the dashboard is given this function as its clock)."""
    return cast(datetime, getattr(_fixtures(), "DEMO_NOW"))


def scratch() -> AbstractContextManager[Path]:
    """A directory with a short path for one organization (see ``dash_worlds.scratch``)."""
    return cast("Callable[[], AbstractContextManager[Path]]", getattr(_fixtures(), "scratch"))()


def queries_of(root: Path, now: Callable[[], datetime] | None = None) -> DashboardQueries:
    """The queries of the dashboard of the organization at ``root``, as the composition root makes them (looked up by name: a package may not import it)."""
    wiring = importlib.import_module("hirearchy.app.wire_dashboard")
    return cast("DashboardQueries", getattr(wiring, "queries_of")(root, now))


def overriding(overrides: Mapping[type, object]) -> AbstractContextManager[None]:
    """``hirearchy.app.wiring.overriding(overrides)``: the ports every runtime opened inside the block starts from (looked up by name: a package may not import it)."""
    return cast("AbstractContextManager[None]", getattr(importlib.import_module("hirearchy.app.wiring"), "overriding")(overrides))


def demo(process_overrides: Callable[[Mapping[type, object]], object], base: Path) -> DemoWorld:
    """The demo organization ``acme`` at ``base``; its scheduler looks running (the fake status is given to ``process_overrides``)."""
    return cast("Callable[[Callable[[Mapping[type, object]], object], Path], DemoWorld]", getattr(_fixtures(), "demo"))(process_overrides, base)


def empty(process_overrides: Callable[[Mapping[type, object]], object], base: Path) -> Organization:
    """An organization that has only its root; its scheduler looks stopped (the fake status is given to ``process_overrides``)."""
    return cast("Callable[[Callable[[Mapping[type, object]], object], Path], Organization]", getattr(_fixtures(), "empty"))(process_overrides, base)
