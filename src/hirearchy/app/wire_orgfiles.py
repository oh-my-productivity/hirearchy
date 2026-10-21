"""Providers of the ``orgfiles`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..access import AccessScopes, AuthorityPolicy
from ..agents import AgentDirectory, AgentRegistry, CharterReader
from ..kernel import AtomicWriter, OrgLayout
from ..orgfiles import OrgFileReader, OrgFileStore, OrgFileWriter
from ..orgfiles._charter_merge import CharterMerger
from ..orgfiles._guard import PathGuard
from ..orgfiles._reader import GuardedOrgFileReader
from ..orgfiles._store import FsOrgFileStore
from ..orgfiles._writer import GuardedOrgFileWriter
from ..settings import OrgSettings
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(OrgFileStore, lambda b: FsOrgFileStore(b.get(OrgLayout), b.get(AtomicWriter)))
    b.provide(
        OrgFileReader,
        lambda b: GuardedOrgFileReader(b.get(OrgLayout), b.get(OrgFileStore), b.get(AgentDirectory), b.get(AccessScopes)),
    )
    b.provide(
        OrgFileWriter,
        lambda b: GuardedOrgFileWriter(
            b.get(OrgLayout),
            b.get(OrgFileStore),
            PathGuard(b.get(OrgLayout), b.get(OrgFileStore), b.get(AgentDirectory)),
            CharterMerger(),
            b.get(AgentDirectory),
            b.get(CharterReader),
            b.get(AgentRegistry),
            b.get(AccessScopes),
            b.get(AuthorityPolicy),
            b.get(OrgSettings),
        ),
    )
