"""The files of the organization that the views look at by name: the message files of a box, and the pid file of the scheduler. (RED: skeleton.)"""

from __future__ import annotations

from pathlib import Path

from ..kernel import OrgLayout
from ._ports import MailboxFiles, SchedulerPidFile


class FsMailboxFiles(MailboxFiles):
    def __init__(self, layout: OrgLayout) -> None:
        self._layout = layout

    def names(self, addr: str, box: str) -> list[str]:
        raise NotImplementedError("red: C-obs-2")

    def path(self, addr: str, box: str, name: str) -> Path:
        raise NotImplementedError("red: C-obs-2")

    def mtime(self, addr: str, box: str, name: str) -> float | None:
        raise NotImplementedError("red: C-obs-2")


class FsSchedulerPidFile(SchedulerPidFile):
    def __init__(self, layout: OrgLayout) -> None:
        self._layout = layout

    def exists(self) -> bool:
        raise NotImplementedError("red: C-obs-2")
