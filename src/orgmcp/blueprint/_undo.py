"""``RetiringRollback``: what an application that failed midway takes back."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..hierarchy import Retirement
from ..kernel import ROOT, OrgError
from ..kernel import depth as org_depth
from ._protocols import BuildUndoing
from ._shapes import Built
from .api import WorkspaceProvisioner


class RetiringRollback(BuildUndoing):
    def __init__(self, agents: AgentDirectory, retirement: Retirement, provisioner: WorkspaceProvisioner) -> None:
        self._agents = agents
        self._retirement = retirement
        self._provisioner = provisioner

    def undo(self, built: Built) -> None:
        for addr in reversed(built.created):
            if self._agents.exists(addr) and org_depth(addr) == 1:
                try:
                    self._retirement.retire(ROOT, addr, "blueprint apply failed midway; rolled back")
                except OrgError:
                    pass
        for p in built.made_dirs:  # directories this call created, if still empty
            if not self._provisioner.remove_if_empty(p):
                break
