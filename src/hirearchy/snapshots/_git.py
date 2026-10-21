"""Git snapshots: the ``git`` program behind ``GitClient``, and the snapshotter built on it."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..kernel import OrgLayout
from .api import GitClient, OrgSnapshotter


class SubprocessGit(GitClient):
    """``git`` run as a child process (``executable`` is looked up on PATH)."""

    def __init__(self, executable: str = "git") -> None:
        self._executable = executable

    def available(self) -> bool:
        return shutil.which(self._executable) is not None

    def has_repository(self, root: Path) -> bool:
        return (root / ".git").exists()

    def init(self, root: Path) -> None:
        subprocess.run([self._executable, "init", "-q"], cwd=root, check=False)

    def commit_all(self, root: Path, message: str) -> None:
        git = [self._executable, "-c", "user.name=hirearchy", "-c", "user.email=hirearchy@localhost"]
        subprocess.run([*git, "add", "-A"], cwd=root, capture_output=True)
        subprocess.run([*git, "commit", "-q", "-m", message], cwd=root, capture_output=True)


class GitOrgSnapshotter(OrgSnapshotter):
    """Snapshots the organization directory (``paths.root``) in the git repository that is there, if any."""

    def __init__(self, paths: OrgLayout, git: GitClient) -> None:
        self._paths = paths
        self._git = git

    def init_repository(self) -> None:
        root = self._paths.root
        if self._git.available() and not self._git.has_repository(root):
            self._git.init(root)

    def commit(self, message: str) -> None:
        root = self._paths.root
        if not self._git.has_repository(root):
            return
        try:
            self._git.commit_all(root, message)
        except OSError:  # no git program, a directory that went away: a snapshot is a convenience, never a reason to fail
            pass
