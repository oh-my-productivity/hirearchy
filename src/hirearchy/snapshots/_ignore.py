"""The ``.gitignore`` of the organization."""

from __future__ import annotations

from collections.abc import Sequence

from ..kernel import AtomicWriter, OrgLayout
from .api import RUNTIME_IGNORE_LINES, IgnoreList


class FsIgnoreList(IgnoreList):
    """``<root>/.gitignore``, written through the injected ``AtomicWriter``."""

    def __init__(self, paths: OrgLayout, writer: AtomicWriter) -> None:
        self._paths = paths
        self._writer = writer

    def write_initial(self, lines: Sequence[str]) -> None:
        self._writer.write(self._paths.root / ".gitignore", "".join(f"{line}\n" for line in lines))

    def ensure(self, lines: Sequence[str]) -> None:
        if not self._paths.root.is_dir():
            return
        path = self._paths.root / ".gitignore"
        try:
            text = path.read_text(encoding="utf-8") if path.exists() else ""
            words = text.split()
            missing = list(dict.fromkeys(line for line in lines if line not in words))
            if missing:
                self._writer.write(path, (text.rstrip("\n") + "\n" if text else "") + "\n".join(missing) + "\n")
        except OSError:
            pass

    def ensure_runtime_files(self) -> None:
        self.ensure(RUNTIME_IGNORE_LINES)
