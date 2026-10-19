"""Every class of ``orgfiles`` is the port it is named for (the checks that need no behaviour; the reader and the writer are checked
by the fixtures of their contract suites)."""

from __future__ import annotations

from pathlib import Path

from orgmcp.agents.testing import MemoryAgents
from orgmcp.kernel import OrgPaths
from orgmcp.kernel.testing import MemoryAtomicWriter
from orgmcp.orgfiles import OrgFileStore
from orgmcp.orgfiles._charter_merge import CharterMerge, CharterMerger
from orgmcp.orgfiles._guard import PathGuard, WriteGuard
from orgmcp.orgfiles._store import FsOrgFileStore
from orgmcp.orgfiles.testing import MemoryOrgFileStore


def test_the_stores_are_org_file_stores() -> None:
    assert isinstance(FsOrgFileStore(OrgPaths(Path("/org")), MemoryAtomicWriter()), OrgFileStore)
    assert isinstance(MemoryOrgFileStore(), OrgFileStore)
    assert isinstance(MemoryOrgFileStore(MemoryAgents()), OrgFileStore)


def test_the_guard_and_the_merger_implement_their_ports() -> None:
    assert issubclass(PathGuard, WriteGuard) and issubclass(CharterMerger, CharterMerge)
