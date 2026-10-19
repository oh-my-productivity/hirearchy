"""The files of the organization that the views look at by name: the message files of a box, and the pid file of the scheduler."""

from __future__ import annotations

import os
from pathlib import Path

from ..kernel import OrgLayout
from ._ports import MailboxFiles, SchedulerPidFile


class FsMailboxFiles(MailboxFiles):
    """The message files in the box directories below the organization."""

    def __init__(self, layout: OrgLayout) -> None:
        self._layout = layout

    def names(self, addr: str, box: str) -> list[str]:
        d = self._layout.box(addr, box)
        return sorted(n for n in os.listdir(d) if n.endswith(".md") and not n.startswith(".")) if d.is_dir() else []

    def path(self, addr: str, box: str, name: str) -> Path:
        return self._layout.box(addr, box) / name

    def mtime(self, addr: str, box: str, name: str) -> float | None:
        try:
            return self.path(addr, box, name).stat().st_mtime
        except OSError:
            return None


class FsSchedulerPidFile(SchedulerPidFile):
    """``.runtime/scheduler.pid``."""

    def __init__(self, layout: OrgLayout) -> None:
        self._layout = layout

    def exists(self) -> bool:
        return (self._layout.runtime_dir() / "scheduler.pid").exists()
