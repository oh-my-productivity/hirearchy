"""What ``strays`` needs to know about the files of a workspace, as a role of its own (so that the probe can be tested without a disk)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class MtimeReader(Protocol):
    def mtime(self, path: Path) -> float | None:
        """The modification time of ``path`` (a file or a directory); None when it cannot be statted (missing, unreadable)."""
        ...


class FsMtimeReader(MtimeReader):
    """``stat`` on the real filesystem."""

    def mtime(self, path: Path) -> float | None:
        try:
            return path.stat().st_mtime
        except OSError:
            return None
