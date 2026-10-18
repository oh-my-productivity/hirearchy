"""``CharterToolNaming``: the names under which an agent has the organization's read and write tools."""

from __future__ import annotations

from ..agents import CharterReader
from .api import ToolNaming


class CharterToolNaming(ToolNaming):
    def __init__(self, charters: CharterReader) -> None:
        self._charters = charters

    def tool_names(self, addr: str) -> dict[str, str]:
        raise NotImplementedError
