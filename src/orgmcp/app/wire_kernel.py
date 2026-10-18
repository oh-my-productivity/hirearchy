"""Providers of the kernel's ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..kernel import AtomicWriter, Clock, Environment, IdGenerator, LedgerStore, OrgLayout, OrgPaths
from ..kernel._system import FsAtomicWriter, FsLedgerStore, OsEnvironment, SystemClock, TimestampIdGenerator
from . import _compat
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(OrgLayout, lambda b: OrgPaths(b.root))
    b.provide(Clock, lambda b: _compat.PatchPointClock() if _compat.ENABLED else SystemClock())
    b.provide(IdGenerator, lambda b: TimestampIdGenerator(b.get(Clock)))
    b.provide(AtomicWriter, lambda b: _compat.PatchPointAtomicWriter() if _compat.ENABLED else FsAtomicWriter())
    b.provide(LedgerStore, lambda b: FsLedgerStore(b.get(OrgLayout), b.get(AtomicWriter)))
    b.provide(Environment, lambda b: OsEnvironment())
