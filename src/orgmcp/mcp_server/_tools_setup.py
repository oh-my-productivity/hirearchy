"""``create_org``: the one tool a root server offers before an organization exists."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ._ports import ToolGroup
from .api import OrgBindingPort
if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

class RootSetupTools(ToolGroup):

    def __init__(self, binding: OrgBindingPort) -> None:
        raise NotImplementedError('red: D-mcp')

    def register(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')
