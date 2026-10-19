"""Notes and budget between neighbours: ``send`` and ``reclaim``."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..budget import BudgetQuery, BudgetReclaimer
from ..dispatch import MessageSender
from ..kernel import ROOT, Provider, parent
from ._ports import ToolGroup
if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

class NoteTools(ToolGroup):

    def __init__(self, sender: Provider[MessageSender], budgets: Provider[BudgetQuery], reclaimer: Provider[BudgetReclaimer]) -> None:
        raise NotImplementedError('red: D-mcp')

    def register(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')
