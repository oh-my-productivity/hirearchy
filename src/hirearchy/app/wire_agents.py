"""Providers of the ``agents`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..agents import AgentDirectory, AgentRegistry, CharterReader, RetiredArchive
from ..agents._charters import FsCharterReader
from ..agents._directory import FsAgentDirectory
from ..agents._registry import FsAgentRegistry
from ..agents._retired import FsRetiredArchive, OsArchiveFiles
from ..kernel import AtomicWriter, OrgLayout
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(AgentDirectory, lambda b: FsAgentDirectory(b.get(OrgLayout)))
    b.provide(CharterReader, lambda b: FsCharterReader(b.get(OrgLayout)))
    b.provide(AgentRegistry, lambda b: FsAgentRegistry(b.get(OrgLayout), b.get(AtomicWriter)))
    b.provide(RetiredArchive, lambda b: FsRetiredArchive(b.get(OrgLayout), OsArchiveFiles()))
