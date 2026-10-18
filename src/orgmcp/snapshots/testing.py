"""In-memory fakes of the snapshot ports, the harnesses of the contract suites, and the registry they iterate over.

``RecordingGit`` is a ``GitClient`` that keeps repositories and commits in memory; ``MemoryIgnoreList`` is an ``IgnoreList`` over one
text. Both pass the same contract suites as the real adapters (``tests/test_contract_*.py``), so a consumer's unit test may use them
instead of the ``git`` program and the filesystem.
"""

from __future__ import annotations

import itertools
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..kernel import OrgPaths
from ..kernel.testing import fs_atomic_writer
from ._git import GitOrgSnapshotter, SubprocessGit
from ._ignore import FsIgnoreList
from .api import RUNTIME_IGNORE_LINES, GitClient, IgnoreList, OrgSnapshotter

AUTHOR = "orgmcp <orgmcp@localhost>"
NO_GIT = "orgmcp-test-no-such-git-program"  # an executable name that exists nowhere


@dataclass(frozen=True)
class GitCommit:
    message: str  # the subject line
    author: str  # "name <email>"
    files: frozenset[str]  # the paths the commit changed, relative to the repository


class RecordingGit(GitClient):
    """git in memory: ``init`` makes a repository, ``commit_all`` commits what ``touch`` marked as changed since the last commit.

    Like the real program it refuses (without raising) a directory that is no repository or whose repository is in ``broken``, makes no
    commit when nothing changed, and raises ``FileNotFoundError`` for every command when it is not ``available``."""

    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.calls: list[tuple[str, ...]] = []  # ("init", root) and ("commit_all", root, message), in order
        self.repositories: set[Path] = set()
        self.commits: dict[Path, list[GitCommit]] = {}
        self.broken: set[Path] = set()  # repositories git refuses to work in
        self._pending: dict[Path, set[str]] = {}

    def touch(self, root: Path, name: str) -> None:
        """Change a file of ``root`` (it will be part of the next commit)."""
        self._pending.setdefault(root, set()).add(name)

    def available(self) -> bool:
        return self._available

    def has_repository(self, root: Path) -> bool:
        return root in self.repositories

    def init(self, root: Path) -> None:
        self.calls.append(("init", str(root)))
        self._run()
        self.repositories.add(root)
        self.commits.setdefault(root, [])

    def commit_all(self, root: Path, message: str) -> None:
        self.calls.append(("commit_all", str(root), message))
        self._run()
        if root not in self.repositories or root in self.broken:
            return  # git: "not a git repository" (exit status 128), ignored
        files = self._pending.pop(root, set())
        if files:
            self.commits[root].append(GitCommit(message, AUTHOR, frozenset(files)))

    def _run(self) -> None:
        if not self._available:
            raise FileNotFoundError(2, "No such file or directory: 'git'")


class MemoryIgnoreList(IgnoreList):
    """``.gitignore`` as one text (``None``: no file); ``directory_exists=False``: the organization directory is gone."""

    def __init__(self, text: str | None = None, directory_exists: bool = True) -> None:
        self.text = text
        self.directory_exists = directory_exists
        self.broken = False  # the file cannot be read or written

    def write_initial(self, lines: Sequence[str]) -> None:
        if self.broken:
            raise OSError(21, "Is a directory")
        self.text = "".join(f"{line}\n" for line in lines)

    def ensure(self, lines: Sequence[str]) -> None:
        if self.broken or not self.directory_exists:
            return
        text = self.text or ""
        words = text.split()
        missing = list(dict.fromkeys(line for line in lines if line not in words))
        if missing:
            self.text = (text.rstrip("\n") + "\n" if text else "") + "\n".join(missing) + "\n"

    def ensure_runtime_files(self) -> None:
        self.ensure(RUNTIME_IGNORE_LINES)


# ------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class GitHarness:
    git: GitClient
    root: Path  # an existing directory, no repository in it
    change: Callable[[str], None]  # change file ``name`` in root (a new file, or new content for an existing one)
    commits: Callable[[], list[GitCommit]]  # the commits of root's repository, oldest first; [] when there is none
    break_repository: Callable[[], None]  # make git refuse every command in root's repository


@dataclass(frozen=True)
class SnapshotHarness:
    snapshotter: OrgSnapshotter
    root: Path
    change: Callable[[str], None]
    commits: Callable[[], list[GitCommit]]
    has_repository: Callable[[], bool]
    make_repository: Callable[[], None]  # a repository that was made outside the snapshotter (git program present)
    break_repository: Callable[[], None]


@dataclass(frozen=True)
class IgnoreHarness:
    ignore: IgnoreList
    read: Callable[[], str | None]  # the text of .gitignore; None when there is no such file
    put: Callable[[str], None]  # replace .gitignore (outside the list)
    break_storage: Callable[[], None]  # make .gitignore unreadable and unwritable
    remove_directory: Callable[[], None]  # the organization directory disappears


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False).stdout


def _real_commits(root: Path) -> list[GitCommit]:
    if not (root / ".git").exists():
        return []
    out = _git(root, "log", "--reverse", "--name-only", "--format=%x01%an <%ae>%x02%s")
    found = []
    for chunk in out.split("\x01")[1:]:
        head, _, rest = chunk.partition("\n")
        author, _, subject = head.partition("\x02")
        found.append(GitCommit(subject, author, frozenset(line for line in rest.splitlines() if line)))
    return found


def _real_change(root: Path) -> Callable[[str], None]:
    counter = itertools.count(1)

    def change(name: str) -> None:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(f"change {next(counter)}\n", encoding="utf-8")

    return change


def _break_real_repository(root: Path) -> None:
    (root / ".git" / "HEAD").write_text("garbage\n", encoding="utf-8")


def _organization(tmp_path: Path) -> Path:
    root = tmp_path / "org"
    root.mkdir()
    return root


def real_git(tmp_path: Path) -> GitHarness:
    root = _organization(tmp_path)
    return GitHarness(SubprocessGit(), root, _real_change(root), lambda: _real_commits(root), lambda: _break_real_repository(root))


def recording_git(tmp_path: Path) -> GitHarness:
    root = _organization(tmp_path)
    git = RecordingGit()
    return GitHarness(git, root, lambda name: git.touch(root, name), lambda: list(git.commits.get(root, [])), lambda: git.broken.add(root))


def _real_snapshotter(tmp_path: Path, executable: str) -> SnapshotHarness:
    root = _organization(tmp_path)
    outside = SubprocessGit()  # the repository the tests make or read does not depend on the snapshotter's git
    return SnapshotHarness(
        GitOrgSnapshotter(OrgPaths(root), SubprocessGit(executable)),
        root,
        _real_change(root),
        lambda: _real_commits(root),
        lambda: outside.has_repository(root),
        lambda: outside.init(root),
        lambda: _break_real_repository(root),
    )


def real_snapshotter(tmp_path: Path) -> SnapshotHarness:
    return _real_snapshotter(tmp_path, "git")


def real_snapshotter_without_git(tmp_path: Path) -> SnapshotHarness:
    return _real_snapshotter(tmp_path, NO_GIT)


def _recording_snapshotter(tmp_path: Path, available: bool) -> SnapshotHarness:
    root = _organization(tmp_path)
    git = RecordingGit(available)

    def make_repository() -> None:  # made outside the snapshotter: whether git is "present" for it does not matter
        git.repositories.add(root)
        git.commits.setdefault(root, [])

    return SnapshotHarness(
        GitOrgSnapshotter(OrgPaths(root), git),
        root,
        lambda name: git.touch(root, name),
        lambda: list(git.commits.get(root, [])),
        lambda: git.has_repository(root),
        make_repository,
        lambda: git.broken.add(root),
    )


def recording_snapshotter(tmp_path: Path) -> SnapshotHarness:
    return _recording_snapshotter(tmp_path, True)


def recording_snapshotter_without_git(tmp_path: Path) -> SnapshotHarness:
    return _recording_snapshotter(tmp_path, False)


def fs_ignore_list(tmp_path: Path) -> IgnoreHarness:
    root = _organization(tmp_path)
    path = root / ".gitignore"

    def put(text: str) -> None:
        path.write_text(text, encoding="utf-8")

    def break_storage() -> None:
        path.unlink(missing_ok=True)
        path.mkdir()

    return IgnoreHarness(
        FsIgnoreList(OrgPaths(root), fs_atomic_writer(tmp_path).writer),
        lambda: path.read_bytes().decode("utf-8") if path.is_file() else None,
        put,
        break_storage,
        lambda: shutil.rmtree(root),
    )


def memory_ignore_list(tmp_path: Path) -> IgnoreHarness:
    ignore = MemoryIgnoreList()

    def put(text: str) -> None:
        ignore.text = text

    def break_storage() -> None:
        ignore.broken = True

    def remove_directory() -> None:
        ignore.directory_exists = False

    return IgnoreHarness(ignore, lambda: ignore.text, put, break_storage, remove_directory)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    GitClient: [real_git, recording_git],
    OrgSnapshotter: [real_snapshotter, recording_snapshotter],
    IgnoreList: [fs_ignore_list, memory_ignore_list],
}

# The same snapshotter when the git program does not exist (the repository, if any, was made outside).
WITHOUT_GIT: Sequence[Callable[[Path], SnapshotHarness]] = [real_snapshotter_without_git, recording_snapshotter_without_git]
