"""Helpers shared by the tests of ``eventlog`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from orgmcp.eventlog import EventFile
from orgmcp.kernel.testing import T0


def at(seconds: float) -> datetime:
    """``T0`` (2026-10-18 10:00 UTC) plus this many seconds."""
    return T0 + timedelta(seconds=seconds)


def day(offset_days: int) -> str:
    """The UTC day, ``YYYY-MM-DD``, that many days after the day of ``T0``."""
    return at(offset_days * 86400).strftime("%Y-%m-%d")


def where(files: Sequence[EventFile]) -> list[tuple[str, str, int]]:
    """(day, proc, pid) of each file: what the tests compare (the path itself differs between the disk and the memory)."""
    return [(f.day, f.proc, f.pid) for f in files]
