"""Providers of the snapshot ports (ARCHITECTURE.md 3.5)."""

from __future__ import annotations

from ..kernel import AtomicWriter, OrgLayout
from ..snapshots import GitClient, IgnoreList, OrgHistory, OrgSnapshotter
from ..snapshots._git import GitOrgHistory, GitOrgSnapshotter, SubprocessGit
from ..snapshots._ignore import FsIgnoreList
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(GitClient, lambda b: SubprocessGit())
    b.provide(OrgSnapshotter, lambda b: GitOrgSnapshotter(b.get(OrgLayout), b.get(GitClient)))
    b.provide(IgnoreList, lambda b: FsIgnoreList(b.get(OrgLayout), b.get(AtomicWriter)))
    b.provide(OrgHistory, lambda b: GitOrgHistory(b.get(OrgLayout), b.get(GitClient)))
