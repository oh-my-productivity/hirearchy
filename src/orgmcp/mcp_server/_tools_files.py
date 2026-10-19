"""The organization's files: ``read`` and ``write``, called ``org_read`` / ``org_write`` for an agent that holds the built-in of the same name."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..access import ToolNaming
from ..kernel import ROOT, OrgLayout, Provider
from ..orgfiles import OrgFileReader, OrgFileWriter
from ._ports import ToolGroup
if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

class FileTools(ToolGroup):

    def __init__(self, naming: Provider[ToolNaming], reader: Provider[OrgFileReader], writer: Provider[OrgFileWriter], layout: Provider[OrgLayout]) -> None:
        raise NotImplementedError('red: D-mcp')

    def register(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')
