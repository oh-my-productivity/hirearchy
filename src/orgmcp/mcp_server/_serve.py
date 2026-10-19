"""The process that serves the tools of one identity over stdio."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..telemetry import ProcessLabel
from ._ports import ServerFactories
from .api import BindingResolver, McpServerRunner


class StdioMcpRunner(McpServerRunner):
    def __init__(self, label: ProcessLabel, resolver: BindingResolver, factories: ServerFactories) -> None:
        self._label = label
        self._resolver = resolver
        self._factories = factories

    def run(self) -> None:
        self._label.set("mcp")
        binding, me = self._resolver.resolve()
        server = self._factories.factory_for(binding).build(me)
        assert isinstance(server, FastMCP)  # (the factory makes no other kind)
        server.run()
