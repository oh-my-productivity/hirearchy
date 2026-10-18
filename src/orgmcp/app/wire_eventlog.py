"""Providers of the ``eventlog`` ports (ARCHITECTURE.md 6.1), and the constructor the legacy modules still need.

The legacy ``observe.py`` helpers that are given a file and no organization (``_tail_events``, ``_head_event``) have no runtime to take
the reader from, so they ask this module for one; they go away with ``observe.py`` (C-obs).
"""

from __future__ import annotations

from pathlib import Path

from ..eventlog import EventFollowers, EventReader
from ..eventlog._follower import FsEventFollowers
from ..eventlog._reader import FsEventReader
from ..kernel import Clock, OrgLayout, OrgPaths
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(EventReader, lambda b: FsEventReader(b.get(OrgLayout)))
    b.provide(EventFollowers, lambda b: FsEventFollowers(b.get(EventReader), b.get(Clock)))


# ------------------------------------------------------------------------------ for the legacy modules (no runtime at hand)


def system_reader() -> EventReader:
    """A disk reader for files that are already named (``tail`` and ``head`` take a file and look at no organization)."""
    return FsEventReader(OrgPaths(Path(".")))
