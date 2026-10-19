"""``FsOrgFileStore``: the files below the organization root, on disk."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..kernel import AtomicWriter, OrgLayout
from .api import FileKind, OrgFileStore


class FsOrgFileStore(OrgFileStore):
    def __init__(self, layout: OrgLayout, writer: AtomicWriter) -> None:
        self._layout = layout
        self._writer = writer

    def resolve(self, path: Path) -> Path:
        raise NotImplementedError

    def kind(self, path: Path) -> FileKind:
        raise NotImplementedError

    def entries(self, path: Path) -> list[str]:
        raise NotImplementedError

    def read_text(self, path: Path, errors: str = "strict") -> str:
        raise NotImplementedError

    def modified(self, path: Path) -> datetime:
        raise NotImplementedError

    def write_text(self, path: Path, text: str) -> None:
        raise NotImplementedError
