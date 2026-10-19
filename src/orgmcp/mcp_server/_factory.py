"""The server for one identity: its instructions, its recorder, the tool groups of its role."""
from __future__ import annotations
from collections.abc import Sequence
from mcp.server.fastmcp import FastMCP
from ..agents import AgentDirectory
from ..kernel import ROOT, OrgError, Provider, norm
from ._ports import ServerInstructions, ToolGroup, ToolRecorder
from .api import McpServerFactory, OrgBindingPort

class GroupedServerFactory(McpServerFactory):
    """``common`` are the groups every identity gets (the service tools decide for themselves whether the identity needs them); ``root_only`` are
    the tools of the human's seat. The order of registration is the order of the tools in the server."""

    def __init__(self, binding: OrgBindingPort, directory: Provider[AgentDirectory], texts: ServerInstructions, recorder: ToolRecorder, common: Sequence[ToolGroup], root_only: Sequence[ToolGroup]) -> None:
        raise NotImplementedError('red: D-mcp')

    def build(self, me: str) -> FastMCP:
        raise NotImplementedError('red: D-mcp')
