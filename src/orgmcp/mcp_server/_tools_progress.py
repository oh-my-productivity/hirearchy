"""``progress``: what the user reads back when they ask "status?", optionally after waiting for a change."""
from __future__ import annotations
from typing import TYPE_CHECKING
import anyio
from ..kernel import Provider
from ..progress import WAIT_MAX, ProgressReporter
from ._ports import SetupMode, ToolGroup
if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

class ProgressTools(ToolGroup):

    def __init__(self, setup: SetupMode, reporter: Provider[ProgressReporter]) -> None:
        raise NotImplementedError('red: D-mcp')

    def register(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')
