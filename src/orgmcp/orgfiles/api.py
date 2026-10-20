"""The public surface of ``orgfiles``: the guard of every file an agent reads or writes inside the organization.

``OrgFileReader`` shows files and directories (inside the organization, and by absolute path inside the workspace and inputs an agent was
granted), ``OrgFileWriter`` is the one way an agent writes (only inside its own directory, never a name the runtime owns), and
``OrgFileStore`` is the port to the files below the organization root as the guard sees them.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

__all__ = [
    "FileKind",
    "OrgFileReader",
    "OrgFileStore",
    "OrgFileWriter",
]

FileKind = Literal["dir", "file", "missing"]


@runtime_checkable
class OrgFileStore(Protocol):
    def resolve(self, path: Path) -> Path:
        """``path`` as an absolute path with symlinks resolved; a relative path is relative to the organization root."""
        ...

    def kind(self, path: Path) -> FileKind:
        """``"dir"``, ``"file"`` (symlinks followed), or ``"missing"`` (also for anything that is neither)."""
        ...

    def entries(self, path: Path) -> list[str]:
        """The names in a directory, hidden ones included, in no particular order; ``[]`` when ``path`` is missing or no directory."""
        ...

    def read_text(self, path: Path, errors: str = "strict") -> str:
        """The file as UTF-8 text; ``errors`` is the handler of ``open`` (``"replace"`` shows what cannot be decoded)."""
        ...

    def modified(self, path: Path) -> datetime:
        """The modification time of a file or directory, aware UTC."""
        ...

    def write_text(self, path: Path, text: str) -> None:
        """Atomically replace the file (parent directories are made), as UTF-8 exactly as given."""
        ...


@runtime_checkable
class OrgFileReader(Protocol):
    def resolve_read(self, path: str, actor: str | None = None) -> Path:
        """Relative paths are relative to the org root. Absolute paths must be inside the organization or, for an agent, inside its
        workspace or inputs or the workspace of an agent in its subtree. Root reads the organization only; ``OrgError`` otherwise."""
        ...

    def read(self, path: str, actor: str | None = None) -> str:
        """A file as a header line (path, words, lines, modification time) and its text, at most 100 000 characters of it; a directory as
        its visible entries, one per line, directories with a trailing ``/``."""
        ...


@runtime_checkable
class OrgFileWriter(Protocol):
    def resolve_write(self, actor: str, path: str) -> Path:
        """The absolute path ``actor`` may write: only inside its own directory (paths are relative to the org root), and no name the
        runtime owns (``OrgError`` with the reason otherwise)."""
        ...

    def write(self, actor: str, path: str, content: str, append: bool = False) -> Path:
        """Write (or append to) a file of the actor's directory; returns its path."""
        ...

    def write_noted(self, actor: str, path: str, content: str, append: bool = False) -> tuple[Path, str]:
        """:meth:`write`, plus a note for the writer (non-empty only for a charter rewrite: which frontmatter keys were kept or changed)."""
        ...
