"""Git snapshots: the ``git`` program behind ``GitClient``, the snapshotter built on it, and the history it reads back."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from ..kernel import OrgLayout
from .api import GitClient, OrgHistory, OrgSnapshotter

_OBJECT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")  # sha1 and sha256 repositories
_NOT_IN_A_PATH = (":", "^", "~", "@{", "\\", "\0")  # revision syntax (``<commit>:<path>``) and a byte no argument can hold
READ_TIMEOUT = 2.0  # seconds a read question to git may take


def is_object_id(text: str) -> bool:
    """``text`` is a full object id: 40 or 64 lowercase hex digits."""
    return _OBJECT_ID.fullmatch(text) is not None


def is_history_path(path: str) -> bool:
    """``path`` can be asked of the history: relative, ``/``-separated, no ``.``, ``..`` or empty segment, not starting with ``-``, and none of
    ``:``, ``^``, ``~``, ``@{``, ``\\`` or NUL in it."""
    return (
        not path.startswith("-")
        and not any(mark in path for mark in _NOT_IN_A_PATH)
        and all(segment not in ("", ".", "..") for segment in path.split("/"))
    )


class SubprocessGit(GitClient):
    """``git`` run as a child process (``executable`` is looked up on PATH). The read questions (``added_by``, ``object_id``, ``cat``) run as
    ``git --literal-pathspecs ...`` in the repository, wait at most ``timeout`` seconds, and answer None on anything but success."""

    def __init__(self, executable: str = "git", timeout: float = READ_TIMEOUT) -> None:
        self._executable = executable
        self.timeout = timeout

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

    def added_by(self, root: Path, path: str) -> str | None:
        out = self._read(root, "log", "--format=%H", "--diff-filter=A", "--", path)
        lines = out.decode("ascii", "replace").split() if out else []
        return lines[-1] if lines and is_object_id(lines[-1]) else None  # newest first: the last line is the oldest commit

    def object_id(self, root: Path, spec: str) -> str | None:
        if not spec or spec.startswith("-"):
            return None
        out = self._read(root, "rev-parse", "--verify", "--quiet", spec)
        found = out.decode("ascii", "replace").strip() if out else ""
        return found if is_object_id(found) else None

    def cat(self, root: Path, obj: str, limit: int) -> bytes | None:
        if not is_object_id(obj):
            return None
        size = self._read(root, "cat-file", "-s", obj)
        if size is None or not size.strip().isdigit() or int(size) > limit:
            return None  # too large, not an object: the blob is not read
        return self._read(root, "cat-file", "blob", obj)

    def _read(self, root: Path, *args: str) -> bytes | None:
        """The output of ``git --literal-pathspecs <args>`` in ``root``; None on a non-zero exit, a timeout or a program that cannot run."""
        try:
            done = subprocess.run(
                [self._executable, "--literal-pathspecs", *args], cwd=root, capture_output=True, timeout=self.timeout, check=False,
            )
        except (OSError, ValueError, subprocess.SubprocessError):  # no program, no directory, an argument git cannot be given, too slow
            return None
        return done.stdout if done.returncode == 0 else None


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


class GitOrgHistory(OrgHistory):
    """The commits of the organization's repository (``paths.root``), read through ``GitClient``. An input that cannot be a path or a commit
    (``OrgHistory``) is answered None without running git, and so is every question when the organization is no repository."""

    def __init__(self, paths: OrgLayout, git: GitClient) -> None:
        self._paths = paths
        self._git = git

    def first_commit_with(self, path: str) -> str | None:
        return self._git.added_by(self._paths.root, path) if is_history_path(path) and self._repository() else None

    def blob(self, commit: str, path: str) -> str | None:
        if not (is_object_id(commit) and is_history_path(path) and self._repository()):
            return None
        return self._git.object_id(self._paths.root, f"{commit}:{path}")

    def text(self, commit: str, path: str, limit: int) -> bytes | None:
        found = self.blob(commit, path)
        return None if found is None else self._git.cat(self._paths.root, found, limit)

    def head(self) -> str | None:
        return self._git.object_id(self._paths.root, "HEAD") if self._repository() else None

    def _repository(self) -> bool:
        try:
            return self._git.has_repository(self._paths.root)
        except OSError:  # a directory that cannot be looked at has no history to read
            return False
