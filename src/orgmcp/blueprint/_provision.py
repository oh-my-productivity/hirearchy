"""``FsWorkspaceProvisioner``: the directories a plan asks for, on disk."""

from __future__ import annotations

from pathlib import Path

from .api import WorkspaceProvisioner


class FsWorkspaceProvisioner(WorkspaceProvisioner):
    def ensure(self, path: Path) -> list[Path]:
        if path.exists():
            return []
        missing = [q for q in (path, *path.parents) if not q.exists()]
        path.mkdir(parents=True, exist_ok=True)
        return missing

    def remove_if_empty(self, path: Path) -> bool:
        try:
            path.rmdir()
        except OSError:
            return False
        return True
