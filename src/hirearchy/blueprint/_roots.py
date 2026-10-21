"""``EnvironmentWorkspaceRoots``: where workspaces and the deliverable path may be."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from ..kernel import Environment, Provider
from ._protocols import WorkspaceRoots


class EnvironmentWorkspaceRoots(WorkspaceRoots):
    def __init__(self, environment: Environment, temp_dir: Provider[Path]) -> None:
        self._environment = environment
        self._temp_dir = temp_dir

    def roots(self, allowed: Sequence[str | Path] | None = None) -> list[Path]:
        if allowed:
            return [Path(r).expanduser().resolve() for r in allowed]
        env = self._environment.get("HIREARCHY_WORKSPACE_ROOTS")
        if env:
            return [Path(r).expanduser().resolve() for r in env.split(os.pathsep) if r]
        cands = [self._environment.home(), self._temp_dir(), Path("/tmp"), self._environment.cwd()]
        return list(dict.fromkeys(c.resolve() for c in cands))
