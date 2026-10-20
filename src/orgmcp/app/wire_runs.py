"""Providers of the ``runs`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..kernel import Clock, LedgerStore, OrgLayout
from ..runs import RunLogReader, RunLogWriter, RunRegistry
from ..runs._reader import FsRunLogReader
from ..runs._registry import FsRunRegistry
from ..runs._writer import FsRunLogWriter
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(RunLogWriter, lambda b: FsRunLogWriter(b.get(OrgLayout), b.get(Clock)))
    b.provide(RunLogReader, lambda b: FsRunLogReader(b.get(OrgLayout)))
    b.provide(RunRegistry, lambda b: FsRunRegistry(b.get(LedgerStore)))
