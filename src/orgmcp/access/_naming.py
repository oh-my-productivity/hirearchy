"""``CharterToolNaming``: the names under which an agent has the organization's read and write tools."""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from ..agents import CharterReader
from ..kernel import ROOT
from .api import ToolNaming


class CharterToolNaming(ToolNaming):
    def __init__(self, charters: CharterReader) -> None:
        self._charters = charters

    def tool_names(self, addr: str) -> dict[str, str]:
        # kiro exposes MCP tools by their plain names, so a built-in ``read``/``write`` of the same name SHADOWS the orgmcp
        # tool (the agent sees only kiro's; studies/F-read-experiment, F2-tool-names). An agent whose charter holds the
        # built-in gets orgmcp's tool as ``org_read`` / ``org_write`` instead; everyone else (and root) keeps the plain names.
        tools = set(cast("Iterable[str]", (self._charters.charter(addr)[0].get("tools") or []) if addr != ROOT else []))
        return {t: (f"org_{t}" if t in tools else t) for t in ("read", "write")}
