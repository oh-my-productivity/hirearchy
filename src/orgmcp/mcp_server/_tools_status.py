"""The state of the organization: ``status`` and ``health``."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..agents import AgentDirectory
from ..daemon import SchedulerStatus
from ..health import HealthAnalyzer, HealthRenderer
from ..kernel import ROOT, OrgError, Provider
from ..overview import OrgTree
from ._ports import SetupMode, ToolGroup
if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

class StatusTools(ToolGroup):

    def __init__(self, setup: SetupMode, tree: Provider[OrgTree], scheduler: Provider[SchedulerStatus], directory: Provider[AgentDirectory], analyzer: Provider[HealthAnalyzer], renderer: Provider[HealthRenderer]) -> None:
        raise NotImplementedError('red: D-mcp')

    def register(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')
