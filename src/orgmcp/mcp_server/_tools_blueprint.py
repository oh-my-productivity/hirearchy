"""The assistant's way to an organization: ``blueprint_example``, ``propose_org`` and ``apply_org``.

The tools only hand over to three roles (the example, the proposal, the application), which hold the rules and the refusal texts."""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING
from ..agents import AgentDirectory
from ..blueprint import BlueprintApplier, BlueprintExamples, BlueprintLoader, PlanIdentity, PlanRenderer
from ..daemon import SchedulerStatus
from ..kernel import Environment, OrgError, OrgLayout, Provider
from ._ports import ExampleLocation, ExampleText, PlanApplication, PlanProposal, PlanTarget, SetupMode, ToolGroup
from .api import OrgBindingPort
if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

class EnvironmentExampleLocation(ExampleLocation):

    def __init__(self, environment: Environment, binding: OrgBindingPort) -> None:
        raise NotImplementedError('red: D-mcp')

    def base(self) -> Path:
        raise NotImplementedError('red: D-mcp')

class TemplateExampleText(ExampleText):

    def __init__(self, examples: Provider[BlueprintExamples], location: ExampleLocation) -> None:
        raise NotImplementedError('red: D-mcp')

    def example(self, kind: str, service: bool) -> str:
        raise NotImplementedError('red: D-mcp')

class BindingPlanTarget(PlanTarget):

    def __init__(self, binding: OrgBindingPort, directory: Provider[AgentDirectory]) -> None:
        raise NotImplementedError('red: D-mcp')

    def line(self) -> str:
        raise NotImplementedError('red: D-mcp')

class RenderedPlanProposal(PlanProposal):

    def __init__(self, loader: Provider[BlueprintLoader], renderer: Provider[PlanRenderer], target: PlanTarget) -> None:
        raise NotImplementedError('red: D-mcp')

    def propose(self, blueprint: str) -> str:
        raise NotImplementedError('red: D-mcp')

class ApprovedPlanApplication(PlanApplication):

    def __init__(self, setup: SetupMode, loader: Provider[BlueprintLoader], identity: Provider[PlanIdentity], applier: Provider[BlueprintApplier], scheduler: Provider[SchedulerStatus], layout: Provider[OrgLayout]) -> None:
        raise NotImplementedError('red: D-mcp')

    def apply(self, blueprint: str, approved: bool, plan_id: str | None) -> str:
        raise NotImplementedError('red: D-mcp')

class BlueprintTools(ToolGroup):

    def __init__(self, examples: ExampleText, proposal: PlanProposal, application: PlanApplication) -> None:
        raise NotImplementedError('red: D-mcp')

    def register(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')
