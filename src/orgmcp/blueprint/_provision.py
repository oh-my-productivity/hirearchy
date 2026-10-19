"""``FsWorkspaceProvisioner``: the directories a plan asks for, on disk."""

from __future__ import annotations

from pathlib import Path

from .api import WorkspaceProvisioner


class FsWorkspaceProvisioner(WorkspaceProvisioner):
    def ensure(self, path: Path) -> list[Path]:
        raise NotImplementedError

    def remove_if_empty(self, path: Path) -> bool:
        raise NotImplementedError
