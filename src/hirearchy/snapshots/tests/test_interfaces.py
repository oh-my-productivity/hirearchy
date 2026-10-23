"""D of SOLID: every class with behaviour subclasses the port it implements (ARCHITECTURE.md R6)."""

from __future__ import annotations

import pytest

from hirearchy.snapshots import GitClient, IgnoreList, OrgHistory, OrgSnapshotter
from hirearchy.snapshots._git import GitOrgHistory, GitOrgSnapshotter, SubprocessGit
from hirearchy.snapshots._ignore import FsIgnoreList
from hirearchy.snapshots.testing import MemoryIgnoreList, MemoryOrgHistory, RecordingGit


@pytest.mark.parametrize(
    ("implementation", "port"),
    [
        (SubprocessGit, GitClient),
        (RecordingGit, GitClient),
        (GitOrgSnapshotter, OrgSnapshotter),
        (GitOrgHistory, OrgHistory),
        (MemoryOrgHistory, OrgHistory),
        (FsIgnoreList, IgnoreList),
        (MemoryIgnoreList, IgnoreList),
    ],
)
def test_the_class_subclasses_its_port(implementation: type, port: type) -> None:
    assert port in implementation.__mro__
