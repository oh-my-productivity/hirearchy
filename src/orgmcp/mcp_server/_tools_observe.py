"""The root-only, read-only tool ``observe``."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..kernel import Provider
from ..observability import ObservabilityText
from ._ports import ToolGroup
if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

class ObservabilityTools(ToolGroup):

    def __init__(self, text: Provider[ObservabilityText]) -> None:
        raise NotImplementedError('red: D-mcp')

    def register(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')
