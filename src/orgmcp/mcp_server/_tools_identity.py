"""Who you are and what is waiting for you: ``whoami`` and ``inbox``."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..daemon import SchedulerStatus
from ..kernel import ROOT, Provider
from ..mail import BatchStore, MailboxReader
from ..prompts import Whoami
from ._ports import SetupMode, ToolGroup
if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

class IdentityTools(ToolGroup):

    def __init__(self, setup: SetupMode, whoami: Provider[Whoami], scheduler: Provider[SchedulerStatus], batches: Provider[BatchStore], mail: Provider[MailboxReader]) -> None:
        raise NotImplementedError('red: D-mcp')

    def register(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')
