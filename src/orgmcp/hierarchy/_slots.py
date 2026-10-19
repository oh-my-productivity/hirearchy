"""Where an agent would live: is something there already (moved from the ``d.exists()`` of ``Org.hire``)."""

from __future__ import annotations

from ..kernel import OrgLayout
from ._ports import AgentSlots


class FsAgentSlots(AgentSlots):
    def __init__(self, paths: OrgLayout) -> None:
        self._paths = paths

    def occupied(self, addr: str) -> bool:
        raise NotImplementedError("B-hierarchy")
