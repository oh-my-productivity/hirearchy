"""``.runtime/scheduler.exit``: why the last scheduler exited by itself."""

from __future__ import annotations

from ..kernel import AtomicWriter, OrgLayout
from .api import ExitMarker


class FileExitMarker(ExitMarker):
    def __init__(self, layout: OrgLayout, writer: AtomicWriter) -> None:
        self._layout = layout
        self._writer = writer

    def write(self, reason: str) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    def read(self) -> str:
        raise NotImplementedError
