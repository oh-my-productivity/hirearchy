"""Helpers shared by the tests of ``eventlog`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from _pytest.mark import ParameterSet

from orgmcp.eventlog import EventFile
from orgmcp.kernel.testing import T0

# While a step is red: the implementations (by factory name) whose contract tests are expected to fail, per Protocol.
RED: dict[str, frozenset[str]] = {
    "EventReader": frozenset({"fs_event_log"}),
    "EventFollower": frozenset({"fs_event_log"}),
    "EventFollowers": frozenset({"fs_event_log"}),
}


def at(seconds: float) -> datetime:
    """``T0`` (2026-10-18 10:00 UTC) plus this many seconds."""
    return T0 + timedelta(seconds=seconds)


def day(offset_days: int) -> str:
    """The UTC day, ``YYYY-MM-DD``, that many days after the day of ``T0``."""
    return at(offset_days * 86400).strftime("%Y-%m-%d")


def implementations(protocol: type, factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """The parameters of a contract fixture: one per implementation, strict xfail for those that are still red."""
    red = RED.get(protocol.__name__, frozenset())
    return [
        pytest.param(f, id=f.__name__, marks=[pytest.mark.xfail(strict=True, reason="red: A-eventlog")] if f.__name__ in red else [])
        for f in factories
    ]


def where(files: Sequence[EventFile]) -> list[tuple[str, str, int]]:
    """(day, proc, pid) of each file: what the tests compare (the path itself differs between the disk and the memory)."""
    return [(f.day, f.proc, f.pid) for f in files]
