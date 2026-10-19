"""Standing services, by role, so a plain worker sees none of them: root and every agent that has direct reports or may hire get ``services``,
``define_service``, ``request`` and ``feedback``; an agent that offers a service gets ``services`` and ``revise_playbook``."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..agents import AgentDirectory, CharterReader
from ..budget import BudgetQuery
from ..kernel import ROOT, Provider, parent
from ..reflection import ServiceReports
from ..services import ServiceCatalog, ServiceCommands
from ._ports import ServiceRoles, SetupMode, ToolGroup
if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

class DirectoryServiceRoles(ServiceRoles):
    """Who needs the service tools, from the directory, the charters and the catalog of services (decided when the server starts)."""

    def __init__(self, setup: SetupMode, directory: Provider[AgentDirectory], charters: Provider[CharterReader], catalog: Provider[ServiceCatalog]) -> None:
        raise NotImplementedError('red: D-mcp')

    def manager(self, me: str) -> bool:
        raise NotImplementedError('red: D-mcp')

    def owner(self, me: str) -> bool:
        raise NotImplementedError('red: D-mcp')

class ServiceTools(ToolGroup):

    def __init__(self, roles: ServiceRoles, reports: Provider[ServiceReports], commands: Provider[ServiceCommands], budgets: Provider[BudgetQuery]) -> None:
        raise NotImplementedError('red: D-mcp')

    def register(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')

    def _register_client_tools(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')

    def _register_owner_tools(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')
