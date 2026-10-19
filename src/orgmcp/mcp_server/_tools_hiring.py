"""Membership of the team: ``hire`` and ``retire``."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..hierarchy import Hiring, Retirement
from ..kernel import Provider
from ._ports import ToolGroup
if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

class HiringTools(ToolGroup):

    def __init__(self, hiring: Provider[Hiring], retirement: Provider[Retirement]) -> None:
        raise NotImplementedError('red: D-mcp')

    def register(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')
