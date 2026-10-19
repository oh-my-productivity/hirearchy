"""``.runtime/scheduler.exit``: why the last scheduler exited by itself."""

from __future__ import annotations

from ..kernel import AtomicWriter, OrgLayout
from ._files import exit_file_of
from .api import ExitMarker


class FileExitMarker(ExitMarker):
    def __init__(self, layout: OrgLayout, writer: AtomicWriter) -> None:
        self._layout = layout
        self._writer = writer

    def write(self, reason: str) -> None:
        self._writer.write(exit_file_of(self._layout), reason + "\n")

    def clear(self) -> None:
        exit_file_of(self._layout).unlink(missing_ok=True)

    def read(self) -> str:
        try:
            return exit_file_of(self._layout).read_text(encoding="utf-8").strip()
        except OSError:
            return ""
