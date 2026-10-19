"""``CharterTeamBuilder``: the workspaces and the agents of a blueprint."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..hierarchy import Hiring
from ._protocols import Charters, TeamBuilding
from ._shapes import Built, Split
from .api import Agent, WorkspaceProvisioner


class CharterTeamBuilder(TeamBuilding):
    def __init__(self, hiring: Hiring, charters: Charters, provisioner: WorkspaceProvisioner) -> None:
        self._hiring = hiring
        self._charters = charters
        self._provisioner = provisioner

    def build(self, agents: Sequence[Agent], bp: Mapping[str, object], split: Mapping[str, Split], built: Built) -> None:
        raise NotImplementedError
