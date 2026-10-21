"""The server for one identity: its instructions, its recorder, the tool groups of its role."""

from __future__ import annotations

from collections.abc import Sequence

from mcp.server.fastmcp import FastMCP

from ..agents import AgentDirectory
from ..kernel import ROOT, OrgError, Provider, norm
from ._ports import ServerInstructions, ToolGroup, ToolRecorder
from .api import McpServerFactory, OrgBindingPort


class GroupedServerFactory(McpServerFactory):
    """``common`` are the groups every identity gets (the service tools decide for themselves whether the identity needs them); ``root_only`` are
    the tools of the human's seat. The order of registration is the order of the tools in the server."""

    def __init__(
        self, binding: OrgBindingPort, directory: Provider[AgentDirectory], texts: ServerInstructions, recorder: ToolRecorder,
        common: Sequence[ToolGroup], root_only: Sequence[ToolGroup],
    ) -> None:
        self._binding = binding
        self._directory = directory
        self._texts = texts
        self._recorder = recorder
        self._common = common
        self._root_only = root_only

    def build(self, me: str) -> FastMCP:
        if self._binding.peek() is not None:
            me = self._directory().require(me)
        elif norm(me) == ROOT:
            me = ROOT  # setup mode
        else:
            raise OrgError(self._binding.missing_message())  # agents never run without their organization
        mcp = FastMCP("hirearchy", instructions=self._texts.for_identity(me))
        self._recorder.instrument(mcp, me)  # every tool registered below (and by anyone later) is recorded
        for group in self._common:
            group.register(mcp, me)
        if me == ROOT:
            for group in self._root_only:
                group.register(mcp, me)
        return mcp
