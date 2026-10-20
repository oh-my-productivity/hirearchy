"""Providers of the kernel's ports (ARCHITECTURE.md 6.1): the system's adapters. A test that needs another clock, other tokens or another writer
replaces the port with ``wiring.overriding`` / ``open_runtime(root, overrides)``; nothing here looks anything up at call time."""

from __future__ import annotations

from ..kernel import AtomicWriter, Clock, Environment, IdGenerator, LedgerStore, OrgLayout, OrgPaths, TokenSource
from ..kernel._system import FsAtomicWriter, FsLedgerStore, OsEnvironment, SecretsTokens, SystemClock, TimestampIdGenerator
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(OrgLayout, lambda b: OrgPaths(b.root))
    b.provide(Clock, lambda b: SystemClock())
    b.provide(TokenSource, lambda b: SecretsTokens())
    b.provide(IdGenerator, lambda b: TimestampIdGenerator(b.get(Clock), b.get(TokenSource).token_hex))
    b.provide(AtomicWriter, lambda b: FsAtomicWriter(b.get(TokenSource).token_hex))
    b.provide(LedgerStore, lambda b: FsLedgerStore(b.get(OrgLayout), b.get(AtomicWriter)))
    b.provide(Environment, lambda b: OsEnvironment())
