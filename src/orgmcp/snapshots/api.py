"""The public surface of ``snapshots``: the organization directory snapshotted in git, and its ``.gitignore``.

Three ports: ``OrgSnapshotter`` (what the runtime asks: start a repository, commit), ``IgnoreList`` (the lines of ``.gitignore``) and
``GitClient`` (the outside world: the ``git`` program). The package is the only writer of ``.git/`` and ``.gitignore`` (ARCHITECTURE.md 2.3).
"""

from __future__ import annotations

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
        """``add -A``, then ``commit -q -m message`` as ``orgmcp <orgmcp@localhost>``. A refusal by git (nothing to commit, not a
        repository) is not an error; a missing git program raises ``OSError``."""
        ...


__all__ = ["GitClient", "IgnoreList", "OrgSnapshotter", "RUNTIME_IGNORE_LINES"]
