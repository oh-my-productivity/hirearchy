"""``FsOrgFileStore``: the files below the organization root, on disk."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from ..kernel import AtomicWriter, OrgLayout
from .api import FileKind, OrgFileStore


class FsOrgFileStore(OrgFileStore):
    def __init__(self, layout: OrgLayout, writer: AtomicWriter) -> None:
        self._layout = layout
        self._writer = writer

    def resolve(self, path: Path) -> Path:
        return (path if path.is_absolute() else self._layout.root / path).resolve()

    def kind(self, path: Path) -> FileKind:
        if path.is_dir():
            return "dir"
        return "file" if path.is_file() else "missing"

    def entries(self, path: Path) -> list[str]:
        try:
            return os.listdir(path)
        except (FileNotFoundError, NotADirectoryError):
            return []

    def read_text(self, path: Path, errors: str = "strict") -> str:
        return path.read_text(encoding="utf-8", errors=errors)

    def modified(self, path: Path) -> datetime:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)

    def write_text(self, path: Path, text: str) -> None:
        self._writer.write(path, text)
