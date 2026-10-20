"""Providers of the ``eventlog`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..eventlog import EventFollowers, EventReader
from ..eventlog._follower import FsEventFollowers
from ..eventlog._reader import FsEventReader
from ..kernel import Clock, OrgLayout
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(EventReader, lambda b: FsEventReader(b.get(OrgLayout)))
    b.provide(EventFollowers, lambda b: FsEventFollowers(b.get(EventReader), b.get(Clock)))
