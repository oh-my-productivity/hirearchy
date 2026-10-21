"""Every class of ``orgfiles`` is the port it is named for (the checks that need no behaviour; the reader and the writer are checked
by the fixtures of their contract suites)."""

from __future__ import annotations

from pathlib import Path

from hirearchy.agents.testing import MemoryAgents
from hirearchy.kernel import OrgPaths
from hirearchy.kernel.testing import MemoryAtomicWriter
from hirearchy.orgfiles import OrgFileStore
from hirearchy.orgfiles._charter_merge import CharterMerge, CharterMerger
from hirearchy.orgfiles._guard import PathGuard, WriteGuard
from hirearchy.orgfiles._store import FsOrgFileStore
from hirearchy.orgfiles.testing import MemoryOrgFileStore


def test_the_stores_are_org_file_stores() -> None:
    assert isinstance(FsOrgFileStore(OrgPaths(Path("/org")), MemoryAtomicWriter()), OrgFileStore)
    assert isinstance(MemoryOrgFileStore(), OrgFileStore)
    assert isinstance(MemoryOrgFileStore(MemoryAgents()), OrgFileStore)


def test_the_guard_and_the_merger_implement_their_ports() -> None:
    assert issubclass(PathGuard, WriteGuard) and issubclass(CharterMerger, CharterMerge)
