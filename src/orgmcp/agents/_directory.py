"""RED skeleton (step A-agents)."""

from __future__ import annotations

from ..kernel import OrgLayout
from ._tree import TreeDirectory


class FsAgentDirectory(TreeDirectory):
    def __init__(self, paths: OrgLayout) -> None:
        raise NotImplementedError("red: A-agents")

    def exists(self, addr: str) -> bool:
        raise NotImplementedError("red: A-agents")

    def children(self, addr: str) -> list[str]:
        raise NotImplementedError("red: A-agents")
