"""Providers of the ``strays`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..access import AccessScopes, ToolNaming
from ..agents import CharterReader
from ..kernel import LedgerStore
from ..strays import StrayProbe, StrayRegistry
from ..strays._ports import FsMtimeReader
from ..strays._probe import WorkspaceStrayProbe
from ..strays._registry import LedgerStrayRegistry
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(StrayProbe, lambda b: WorkspaceStrayProbe(b.get(AccessScopes), b.get(CharterReader), FsMtimeReader()))
    b.provide(StrayRegistry, lambda b: LedgerStrayRegistry(b.get(LedgerStore), b.get(ToolNaming)))
