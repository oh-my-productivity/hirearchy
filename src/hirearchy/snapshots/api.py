"""The public surface of ``snapshots``: the organization directory snapshotted in git, its ``.gitignore``, and its history read back.

Four ports: ``OrgSnapshotter`` (what the runtime asks: start a repository, commit), ``IgnoreList`` (the lines of ``.gitignore``), ``OrgHistory``
(read-only questions to the commits already made) and ``GitClient`` (the outside world: the ``git`` program). The package is the only writer of
``.git/`` and ``.gitignore`` (ARCHITECTURE.md 2.3); ``OrgHistory`` never writes.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

# The lines ``IgnoreList.ensure_runtime_files`` adds when they are missing: files that change constantly stay out of the snapshots
# (``git add -A`` runs after every run). They are paths inside ``.runtime/``.
RUNTIME_IGNORE_LINES: tuple[str, ...] = (
    ".runtime/running.json",
    ".runtime/scheduler.log",
    ".runtime/scheduler.exit",
    ".runtime/events/",
)


@runtime_checkable
class OrgSnapshotter(Protocol):
    def init_repository(self) -> None:
        """``git init`` (when git exists and there is no repository yet)."""
        ...

    def commit(self, message: str) -> None:
        """``add -A`` + commit when the organization is a repository; nothing otherwise. Never raises."""
        ...


@runtime_checkable
class IgnoreList(Protocol):
    def write_initial(self, lines: Sequence[str]) -> None:
        """Create ``.gitignore`` with these lines (each followed by a newline), replacing what is there."""
        ...

    def ensure(self, lines: Sequence[str]) -> None:
        """Append the lines that are missing (whole-line match) after the existing text. Never raises."""
        ...

    def ensure_runtime_files(self) -> None:
        """``ensure(RUNTIME_IGNORE_LINES)``: ``running.json``, ``scheduler.log``, ``scheduler.exit``, ``events/``."""
        ...


@runtime_checkable
class OrgHistory(Protocol):
    """Read-only questions to the organization's git history. Every method answers None when there is no repository, no git, or no answer;
    none raises and none writes. A ``path`` is relative to the organization and ``/``-separated, without a ``.``, ``..`` or empty segment,
    not starting with ``-`` and holding none of ``:``, ``^``, ``~``, ``@{`` and ``\\`` (so the ``<commit>:<path>`` spec can never be read as
    revision syntax); a ``commit`` is a full object id, 40 or 64 lowercase hex digits. Anything else is answered None without asking git."""

    def first_commit_with(self, path: str) -> str | None:
        """The id of the oldest commit that added ``path``."""
        ...

    def blob(self, commit: str, path: str) -> str | None:
        """The object id of ``path`` at ``commit``; None when nothing is there. (A directory answers its tree's id, which equals no blob id.)"""
        ...

    def text(self, commit: str, path: str, limit: int) -> bytes | None:
        """The bytes of the file ``path`` at ``commit``; None when absent, not a file, or larger than ``limit`` bytes."""
        ...

    def head(self) -> str | None:
        """The commit ``HEAD`` names now (the key under which a caller memoizes a None answer: it can change only with a new commit)."""
        ...


@runtime_checkable
class GitClient(Protocol):
    """The port to the outside world: the ``git`` program, one repository per directory."""

    def available(self) -> bool:
        """git is on PATH."""
        ...

    def has_repository(self, root: Path) -> bool:
        """``root/.git`` exists."""
        ...

    def init(self, root: Path) -> None:
        """``git init -q`` in ``root``."""
        ...

    def commit_all(self, root: Path, message: str) -> None:
        """``add -A``, then ``commit -q -m message`` as ``hirearchy <hirearchy@localhost>``. A refusal by git (nothing to commit, not a
        repository) is not an error; a missing git program raises ``OSError``."""
        ...

    def added_by(self, root: Path, path: str) -> str | None:
        """The id of the oldest commit of ``root``'s repository that added ``path`` (relative to ``root``; read literally, never as a glob or a
        pathspec magic). None when there is no repository, no git, no such path, a failure or a timeout; never raises."""
        ...

    def object_id(self, root: Path, spec: str) -> str | None:
        """The object id ``spec`` names (``HEAD``, or ``<commit>:<path>``), verified to exist; None when it does not, when ``spec`` is empty or
        starts with ``-``, on a failure or a timeout; never raises."""
        ...

    def cat(self, root: Path, obj: str, limit: int) -> bytes | None:
        """The content of the blob ``obj`` (a full object id) when its size is at most ``limit`` bytes (the size is asked before the blob is
        read); None when it is larger, is no blob, on a failure or a timeout; never raises."""
        ...


def blob_id(data: bytes, hexlen: int = 40) -> str:
    """The git object id of a blob with these bytes, as ``git hash-object`` computes it (pure): ``sha1(b"blob <size>\\0" + data)`` for ``hexlen``
    40, ``sha256`` for 64 (a repository's own object format; the caller passes the length of the id it compares with). Any other length is a
    ``ValueError`` (a bug of the caller)."""
    if hexlen not in (40, 64):
        raise ValueError(f"a git object id has 40 or 64 hex digits, not {hexlen}")
    digest = hashlib.sha1 if hexlen == 40 else hashlib.sha256
    return digest(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


__all__ = ["GitClient", "IgnoreList", "OrgHistory", "OrgSnapshotter", "RUNTIME_IGNORE_LINES", "blob_id"]
