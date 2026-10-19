"""``FsTextFiles``: blueprint files on disk."""
from __future__ import annotations
from pathlib import Path
from ._protocols import TextFiles

class FsTextFiles(TextFiles):

    def is_file(self, path: Path) -> bool:
        raise NotImplementedError('red: C-blueprint-1')

    def read(self, path: Path) -> str:
        raise NotImplementedError('red: C-blueprint-1')
