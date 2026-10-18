"""Git snapshots: the git program behind ``GitClient`` and the snapshotter built on it (RED skeleton: nothing is implemented yet)."""

from __future__ import annotations

from pathlib import Path

from ..kernel import OrgLayout
from .api import GitClient, OrgSnapshotter


class SubprocessGit(GitClient):
    def __init__(self, executable: str = "git") -> None:
        self._executable = executable

    def available(self) -> bool:
        raise NotImplementedError

    def has_repository(self, root: Path) -> bool:
        raise NotImplementedError

    def init(self, root: Path) -> None:
        raise NotImplementedError

    def commit_all(self, root: Path, message: str) -> None:
        raise NotImplementedError


class GitOrgSnapshotter(OrgSnapshotter):
    def __init__(self, paths: OrgLayout, git: GitClient) -> None:
        self._paths = paths
        self._git = git

    def init_repository(self) -> None:
        raise NotImplementedError

    def commit(self, message: str) -> None:
        raise NotImplementedError
