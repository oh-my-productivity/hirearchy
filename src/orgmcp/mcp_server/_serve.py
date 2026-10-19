"""The process that serves the tools of one identity over stdio."""
from __future__ import annotations
from mcp.server.fastmcp import FastMCP
from ..telemetry import ProcessLabel
from ._ports import ServerFactories
from .api import BindingResolver, McpServerRunner

class StdioMcpRunner(McpServerRunner):

    def __init__(self, label: ProcessLabel, resolver: BindingResolver, factories: ServerFactories) -> None:
        raise NotImplementedError('red: D-mcp')

    def run(self) -> None:
        raise NotImplementedError('red: D-mcp')
