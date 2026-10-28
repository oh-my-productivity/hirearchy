"""In-memory fakes of the snapshot ports, the harnesses of the contract suites, and the registry they iterate over.

``RecordingGit`` is a ``GitClient`` that keeps repositories, commits and the content of their files in memory; ``MemoryIgnoreList`` is an
``IgnoreList`` over one text; ``MemoryOrgHistory`` is an ``OrgHistory`` over a list of commits. All pass the same contract suites as the real
adapters (``tests/test_contract_*.py``), so a consumer's unit test may use them instead of the ``git`` program and the filesystem.
"""

from __future__ import annotations

import hashlib
import itertools
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..kernel import OrgPaths
from ..kernel.testing import fs_atomic_writer
from ._git import GitOrgHistory, GitOrgSnapshotter, SubprocessGit, is_history_path, is_object_id
from ._ignore import FsIgnoreList
from .api import RUNTIME_IGNORE_LINES, Change, GitClient, IgnoreList, OrgHistory, OrgSnapshotter, blob_id

AUTHOR = "hirearchy <hirearchy@localhost>"
FIRST_COMMIT_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)  # the fakes' commits are one minute apart from here, in order


def commit_time(position: int) -> datetime:
    """The time the fakes give the commit at ``position`` (0 is the oldest)."""
    return FIRST_COMMIT_TIME + timedelta(minutes=position)
NO_GIT = "hirearchy-test-no-such-git-program"  # an executable name that exists nowhere


@dataclass(frozen=True)
class GitCommit:
    message: str  # the subject line
    author: str  # "name <email>"
    files: frozenset[str]  # the paths the commit changed, relative to the repository


class RecordingGit(GitClient):
    """git in memory: ``init`` makes a repository, ``commit_all`` commits what ``touch`` marked as changed since the last commit.

    Like the real program it refuses (without raising) a directory that is no repository or whose repository is in ``broken``, makes no
    commit when nothing changed, and raises ``FileNotFoundError`` for every command when it is not ``available``. The read questions answer
    None in all those cases, as the real ones do. ``touch(root, name, data)`` also sets the content of the file, which each commit keeps (a
    whole tree, as ``add -A`` does), and the object ids are git's own (``blob_id``; a commit's id is made up from its position and message).
    Differences from git: a directory has no object id here, and a commit id is not a hash of its content."""

    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.calls: list[tuple[str, ...]] = []  # ("init", root) and ("commit_all", root, message), in order
        self.reads: list[tuple[str, ...]] = []  # ("added_by", root, path), ("object_id", root, spec), ("cat", root, obj, limit), ("log", root,
        # limit, *paths), in order
        self.repositories: set[Path] = set()
        self.commits: dict[Path, list[GitCommit]] = {}
        self.broken: set[Path] = set()  # repositories git refuses to work in
        self._pending: dict[Path, set[str]] = {}
        self._work: dict[Path, dict[str, bytes]] = {}  # the files as they are now
        self._trees: dict[Path, list[tuple[str, dict[str, bytes]]]] = {}  # per repository: (commit id, its whole tree), oldest first

    def touch(self, root: Path, name: str, data: bytes | None = None) -> None:
        """Change a file of ``root`` (it will be part of the next commit); ``data`` is its new content (the old one, or empty, when omitted)."""
        self._pending.setdefault(root, set()).add(name)
        work = self._work.setdefault(root, {})
        work[name] = work.get(name, b"") if data is None else data

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
            trees = self._trees.setdefault(root, [])  # a repository made outside ``init`` (``repositories.add``) has none yet
            made = hashlib.sha1(f"commit {len(trees)} {root} {message}".encode(), usedforsecurity=False).hexdigest()
            trees.append((made, dict(self._work.get(root, {}))))

    def added_by(self, root: Path, path: str) -> str | None:
        self.reads.append(("added_by", str(root), path))
        for commit, tree in self._history(root):
            if path in tree:
                return commit  # the first tree that has it: the commit that added it
        return None

    def object_id(self, root: Path, spec: str) -> str | None:
        self.reads.append(("object_id", str(root), spec))
        history = self._history(root)
        if spec == "HEAD":
            return history[-1][0] if history else None
        commit, _, path = spec.partition(":")
        tree = next((t for c, t in history if c == commit), None) if is_object_id(commit) else None
        return blob_id(tree[path], len(commit)) if tree is not None and path in tree else None

    def cat(self, root: Path, obj: str, limit: int) -> bytes | None:
        self.reads.append(("cat", str(root), obj, str(limit)))
        if not is_object_id(obj):
            return None
        found = next((data for _, tree in self._history(root) for data in tree.values() if blob_id(data, len(obj)) == obj), None)
        if found is None:  # a commit: the text git prints for it, its message after the blank line
            history = self._history(root)
            found = next((self._commit_text(root, position) for position, (made, _) in enumerate(history) if made == obj), None)
        return found if found is not None and len(found) <= limit else None

    def _commit_text(self, root: Path, position: int) -> bytes:
        stamp = f"{int(commit_time(position).timestamp())} +0000"
        return f"tree {'0' * 40}\nauthor {AUTHOR} {stamp}\ncommitter {AUTHOR} {stamp}\n\n{self.commits[root][position].message}\n".encode()

    def log(self, root: Path, paths: Sequence[str], limit: int) -> bytes | None:
        self.reads.append(("log", str(root), str(limit), *paths))
        if not paths or limit < 1:
            return b""
        history = self._history(root)
        if not history:
            return None
        out = b""
        listed = 0
        for position in reversed(range(len(history))):  # newest first; the commits of ``commits`` and the trees are made together
            changed = sorted(self.commits[root][position].files.intersection(paths))
            if changed and listed < limit:
                out += f"\0{history[position][0]}\t{commit_time(position).isoformat()}\n\n".encode() + "".join(f"{p}\n" for p in changed).encode()
                listed += 1
        return out

    def _history(self, root: Path) -> list[tuple[str, dict[str, bytes]]]:
        """The commits git would answer from: none when git is missing, ``root`` is no repository or its repository is broken."""
        if not self._available or root not in self.repositories or root in self.broken:
            return []
        return self._trees.get(root, [])

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


class MemoryOrgHistory(OrgHistory):
    """The history of an organization as a list of commits, each holding a whole tree. ``commit`` adds one; the questions follow the same rules
    as ``GitOrgHistory`` (an input that cannot be a path or a commit is answered None) with git's own object ids for the blobs."""

    def __init__(self) -> None:
        self._commits: list[tuple[str, dict[str, bytes]]] = []
        self._changed: list[tuple[datetime, frozenset[str]]] = []  # per commit: its time and the paths whose content it changed
        self._messages: dict[str, str] = {}  # commit id -> message

    def commit(self, files: Mapping[str, bytes | None], when: datetime | None = None, message: str = "test commit") -> str:
        """A new commit: the tree of the last one with ``files`` changed (a value of None deletes the file). Returns its id. ``when`` is its time
        (``commit_time`` of its position, with its offset, when omitted); ``message`` its message."""
        before = self._commits[-1][1] if self._commits else {}
        tree = dict(before)
        for name, data in files.items():
            if data is None:
                tree.pop(name, None)
            else:
                tree[name] = data
        made = hashlib.sha1(f"memory commit {len(self._commits)}".encode(), usedforsecurity=False).hexdigest()
        self._changed.append((commit_time(len(self._commits)) if when is None else when, frozenset(n for n in files if before.get(n) != tree.get(n))))
        self._commits.append((made, tree))
        self._messages[made] = message
        return made

    def first_commit_with(self, path: str) -> str | None:
        return next((c for c, tree in self._commits if is_history_path(path) and path in tree), None)

    def blob(self, commit: str, path: str) -> str | None:
        data = self._data(commit, path)
        return None if data is None else blob_id(data, len(commit))

    def text(self, commit: str, path: str, limit: int) -> bytes | None:
        data = self._data(commit, path)
        return data if data is not None and len(data) <= limit else None

    def head(self) -> str | None:
        return self._commits[-1][0] if self._commits else None

    def subject(self, commit: str) -> str | None:
        return self._messages[commit].partition("\n")[0] if is_object_id(commit) and commit in self._messages else None

    def changes(self, paths: Sequence[str], limit: int) -> list[Change] | None:
        if not self._commits:
            return None
        asked = [path for path in dict.fromkeys(paths) if is_history_path(path)]
        found: list[Change] = []
        listed = 0
        for (commit_id, _), (when, changed) in zip(reversed(self._commits), reversed(self._changed), strict=True):
            names = [path for path in sorted(asked) if path in changed]
            if names and listed < limit:
                found.extend(Change(commit_id, when, name) for name in names)
                listed += 1
        return found

    def _data(self, commit: str, path: str) -> bytes | None:
        if not (is_object_id(commit) and is_history_path(path)):
            return None
        tree = next((t for c, t in self._commits if c == commit), None)
        return None if tree is None else tree.get(path)


# ------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class GitHarness:
    git: GitClient
    root: Path  # an existing directory, no repository in it
    change: Callable[[str], None]  # change file ``name`` in root (a new file, or new content for an existing one)
    commits: Callable[[], list[GitCommit]]  # the commits of root's repository, oldest first; [] when there is none
    break_repository: Callable[[], None]  # make git refuse every command in root's repository
    read: Callable[[str], bytes]  # the content ``change`` last gave file ``name`` (what the next commit holds)


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
class HistoryHarness:
    history: OrgHistory
    commit: Callable[..., str]  # (files, message="test commit"): a commit with these files changed (None deletes one); the first makes the repository; its id
    # before the first ``commit`` there is no repository: every question is answered None


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
    return GitHarness(
        SubprocessGit(), root, _real_change(root), lambda: _real_commits(root), lambda: _break_real_repository(root), lambda name: (root / name).read_bytes(),
    )


def recording_git(tmp_path: Path) -> GitHarness:
    root = _organization(tmp_path)
    git = RecordingGit()
    counter = itertools.count(1)

    def change(name: str) -> None:
        git.touch(root, name, f"change {next(counter)}\n".encode())

    return GitHarness(git, root, change, lambda: list(git.commits.get(root, [])), lambda: git.broken.add(root), lambda name: git._work[root][name])


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


def real_org_history(tmp_path: Path) -> HistoryHarness:
    root = _organization(tmp_path)
    git = SubprocessGit()

    def commit(files: Mapping[str, bytes | None], message: str = "test commit") -> str:
        if not git.has_repository(root):
            git.init(root)
        for name, data in files.items():
            if data is None:
                (root / name).unlink(missing_ok=True)
            else:
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes(data)
        git.commit_all(root, message)
        head = git.object_id(root, "HEAD")
        assert head is not None
        return head

    return HistoryHarness(GitOrgHistory(OrgPaths(root), git), commit)


def memory_org_history(tmp_path: Path) -> HistoryHarness:
    history = MemoryOrgHistory()
    return HistoryHarness(history, history.commit)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    GitClient: [real_git, recording_git],
    OrgHistory: [real_org_history, memory_org_history],
    OrgSnapshotter: [real_snapshotter, recording_snapshotter],
    IgnoreList: [fs_ignore_list, memory_ignore_list],
}

# The same snapshotter when the git program does not exist (the repository, if any, was made outside).
WITHOUT_GIT: Sequence[Callable[[Path], SnapshotHarness]] = [real_snapshotter_without_git, recording_snapshotter_without_git]
