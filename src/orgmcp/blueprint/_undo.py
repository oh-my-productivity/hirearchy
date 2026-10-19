"""``RetiringRollback``: what an application that failed midway takes back."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..hierarchy import Retirement
from ._protocols import BuildUndoing
from ._shapes import Built
from .api import WorkspaceProvisioner


class RetiringRollback(BuildUndoing):
    def __init__(self, agents: AgentDirectory, retirement: Retirement, provisioner: WorkspaceProvisioner) -> None:
        self._agents = agents
        self._retirement = retirement
        self._provisioner = provisioner

    def undo(self, built: Built) -> None:
        raise NotImplementedError
