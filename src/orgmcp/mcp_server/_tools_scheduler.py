"""``start`` and ``stop``: the scheduler of the organization, from the human's seat."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..attention import OpenWork, WaitingOnUser
from ..daemon import SchedulerControl, SchedulerStatus
from ..kernel import OrgLayout, Provider
from ._ports import ToolGroup
if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

class SchedulerTools(ToolGroup):

    def __init__(self, control: Provider[SchedulerControl], status: Provider[SchedulerStatus], waiting: Provider[WaitingOnUser], work: Provider[OpenWork], layout: Provider[OrgLayout]) -> None:
        raise NotImplementedError('red: D-mcp')

    def register(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')
