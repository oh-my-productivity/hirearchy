"""Charters and memories as files: ``<addr>/AGENT.md`` and ``<addr>/MEMORY.md``."""

from __future__ import annotations

from ..kernel import ROOT, JsonObject, OrgLayout, norm
from ._tree import parse_charter, root_charter
from .api import CharterReader


class FsCharterReader(CharterReader):
    def __init__(self, paths: OrgLayout) -> None:
        self._paths = paths

    def charter(self, addr: str) -> tuple[JsonObject, str]:
        a = norm(addr)
        if a == ROOT:
            return root_charter()
        return parse_charter((self._paths.agent_dir(a) / "AGENT.md").read_text(encoding="utf-8"))

    def memory(self, addr: str) -> str:
        p = self._paths.agent_dir(addr) / "MEMORY.md"
        return p.read_text(encoding="utf-8") if p.is_file() else ""
