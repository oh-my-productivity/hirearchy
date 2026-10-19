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

    def roots(self, allowed: Sequence[str | Path] | None=None) -> list[Path]:
        raise NotImplementedError('red: C-blueprint-1')
