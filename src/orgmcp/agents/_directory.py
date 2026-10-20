"""The agents as directories: an agent is a directory with an ``AGENT.md``, below the directory of its parent."""

from __future__ import annotations

from ..kernel import ROOT, OrgLayout, child_addr, norm
from ._tree import TreeDirectory, valid_address


class FsAgentDirectory(TreeDirectory):
    def __init__(self, paths: OrgLayout) -> None:
        self._paths = paths

    def exists(self, addr: str) -> bool:
        a = norm(addr)
        if a == ROOT:
            return True
        if not valid_address(a):
            return False
        return (self._paths.agent_dir(a) / "AGENT.md").is_file()

    def children(self, addr: str) -> list[str]:
        a = norm(addr)
        d = self._paths.agent_dir(a)
        if not d.is_dir():
            return []
        return [child_addr(a, p.name) for p in sorted(d.iterdir()) if p.is_dir() and valid_address(p.name) and (p / "AGENT.md").is_file()]
