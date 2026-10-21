"""Helpers of the tests of ``mcp_server``: calling the tools of a server the way a client does."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from hirearchy.mcp_server._ports import ToolGroup

def call(server: FastMCP, tool: str, **arguments: Any) -> str:
    """The text a client gets from calling ``tool``."""
    result = asyncio.run(server.call_tool(tool, arguments))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(block, "text", "") for block in blocks)


def fails(server: FastMCP, tool: str, **arguments: Any) -> str:
    """The text of the refusal when calling ``tool`` fails."""
    with pytest.raises(Exception) as info:
        call(server, tool, **arguments)
    return str(info.value)


def names(server: FastMCP) -> list[str]:
    """The names of the tools of a server, in the order they were registered."""
    return [tool.name for tool in asyncio.run(server.list_tools())]


def serve(group: ToolGroup, me: str) -> FastMCP:
    """A server with only this group registered for ``me``."""
    server = FastMCP("test")
    group.register(server, me)
    return server


def described(server: FastMCP) -> dict[str, str]:
    return {tool.name: tool.description or "" for tool in asyncio.run(server.list_tools())}


Factory = Callable[..., object]
