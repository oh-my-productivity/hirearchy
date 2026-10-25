"""The state of the organization: ``status`` and ``health``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..access import ModelFloorAudit
from ..agents import AgentDirectory
from ..daemon import SchedulerStatus
from ..health import HealthAnalyzer, HealthRenderer
from ..kernel import ROOT, OrgError, Provider
from ..overview import OrgTree
from ..reflection import DeliverableChecks
from ._ports import InstalledSkill, SetupMode, ToolGroup
from ._tools_identity import with_deliverables_note, with_floor_note, with_stale_skill_note

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class StatusTools(ToolGroup):
    def __init__(
        self, setup: SetupMode, tree: Provider[OrgTree], scheduler: Provider[SchedulerStatus], directory: Provider[AgentDirectory],
        analyzer: Provider[HealthAnalyzer], renderer: Provider[HealthRenderer], skill: InstalledSkill, deliverables: Provider[DeliverableChecks],
        floor: Provider[ModelFloorAudit],
    ) -> None:
        self._setup = setup
        self._tree = tree
        self._scheduler = scheduler
        self._directory = directory
        self._analyzer = analyzer
        self._renderer = renderer
        self._skill = skill
        self._deliverables = deliverables
        self._floor = floor

    def register(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def status() -> str:
            """The whole organization as a tree: each agent's role, state, budget and workload."""
            if me == ROOT and self._setup.active():
                return with_stale_skill_note(self._setup.state(), self._skill)
            tree = self._tree().tree()
            if me != ROOT:
                return tree
            shown = with_deliverables_note(f"{tree}\n\n{self._scheduler().describe()}", self._deliverables())
            return with_stale_skill_note(with_floor_note(shown, self._floor()), self._skill)

        @mcp.tool()
        def health(agent: str | None = None) -> str:
            """Health report (stuck, expensive, low-quality, wasteful, idle, paused) for an agent and its subtree.

        agent: yourself or an agent in your own subtree (root may ask about anyone). Default: your own subtree
        (root: the whole organization). Use it to decide whom to follow up with, rework, re-budget or retire.
        """
            directory = self._directory()
            target = directory.require(agent or me)
            if me != ROOT and target not in directory.subtree(me):
                raise OrgError(f"you can only view health for yourself or agents in your own subtree ({me}/...), not {target}")
            return self._renderer().render_text(self._analyzer().org_health(target), causes=me == ROOT)
