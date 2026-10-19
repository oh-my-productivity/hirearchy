"""Work down and results up: ``delegate`` and ``report``."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..budget import BudgetQuery
from ..dispatch import TaskAssigner, TaskReporter
from ..kernel import Provider
from ..mail import MailboxReader
from ..services import ServiceHints
from ._ports import ToolGroup
if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

class TaskTools(ToolGroup):

    def __init__(self, assigner: Provider[TaskAssigner], reporter: Provider[TaskReporter], budgets: Provider[BudgetQuery], mail: Provider[MailboxReader], hints: Provider[ServiceHints]) -> None:
        raise NotImplementedError('red: D-mcp')

    def register(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')
