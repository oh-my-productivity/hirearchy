"""Providers of the ``agents`` ports (ARCHITECTURE.md 6.1), and the dashboard's lenient variant for the legacy ``LenientOrg``.

``lenient`` goes away with ``LenientOrg`` (C-dashdata), whose caching roles are these decorators.
"""

from __future__ import annotations

import dataclasses
from collections.abc import MutableMapping

from ..agents import AgentDirectory, AgentRegistry, CharterReader, RetiredArchive
from ..agents._caching import CachingAgentDirectory, DirectoryProbe, FsCharterStamps, LenientCharterReader
from ..agents._charters import FsCharterReader
from ..agents._directory import FsAgentDirectory
from ..agents._registry import FsAgentRegistry
from ..agents._retired import FsRetiredArchive, OsArchiveFiles
from ..kernel import AtomicWriter, OrgLayout
from ._builder import Builder
from .runtime import OrgRuntime


def register(b: Builder) -> None:
    b.provide(AgentDirectory, lambda b: FsAgentDirectory(b.get(OrgLayout)))
    b.provide(CharterReader, lambda b: FsCharterReader(b.get(OrgLayout)))
    b.provide(AgentRegistry, lambda b: FsAgentRegistry(b.get(OrgLayout), b.get(AtomicWriter)))
    b.provide(RetiredArchive, lambda b: FsRetiredArchive(b.get(OrgLayout), OsArchiveFiles()))


def lenient(runtime: OrgRuntime, probe: DirectoryProbe, problems: MutableMapping[str, str]) -> OrgRuntime:
    """``runtime`` with the dashboard's decorators on the read ports of the agents: the children listed per change of the directory
    (``probe`` tells when), the charters parsed per change of the file, unreadable ones reported in ``problems``."""
    return dataclasses.replace(
        runtime,
        agents=CachingAgentDirectory(runtime.agents, probe, runtime.clock),
        charters=LenientCharterReader(runtime.charters, FsCharterStamps(runtime.paths), problems),
    )
