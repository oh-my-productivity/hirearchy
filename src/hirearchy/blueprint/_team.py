"""``CharterTeamBuilder``: the workspaces and the agents of a blueprint."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ..hierarchy import Hiring
from ..kernel import ROOT
from ._protocols import Charters, TeamBuilding
from ._shapes import Built, Split
from .api import Agent, WorkspaceProvisioner


class CharterTeamBuilder(TeamBuilding):
    def __init__(self, hiring: Hiring, charters: Charters, provisioner: WorkspaceProvisioner) -> None:
        self._hiring = hiring
        self._charters = charters
        self._provisioner = provisioner

    def build(
        self, agents: Sequence[Agent], bp: Mapping[str, object], split: Mapping[str, Split], built: Built, approved_in: str | None = None,
    ) -> None:
        for a in agents:  # parents before children
            if a.workspace:
                built.made_dirs += self._provisioner.ensure(Path(a.workspace))
            addr = self._hiring.hire(
                a.parent or ROOT, a.name, a.role, self._charters.charter(a, agents, bp, split), model=a.model, tools=a.tools,
                can_hire=a.can_hire, max_children=a.max_children, workspace=a.workspace,
                inputs=a.inputs if (a.inputs or "read" in a.tools) else None, approved=True,  # the approved plan grants the positions in it
                kind=a.kind, approved_in=approved_in,
            )
            built.created.append(addr)
