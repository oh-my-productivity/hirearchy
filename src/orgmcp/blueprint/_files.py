"""``FsTextFiles``: blueprint files on disk."""

from __future__ import annotations

from pathlib import Path

from ._protocols import TextFiles


class FsTextFiles(TextFiles):
    def is_file(self, path: Path) -> bool:
        return path.is_file()

    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")
