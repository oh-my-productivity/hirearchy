"""The organization a blueprint is planned against: the real one, or none yet."""
from __future__ import annotations
from pathlib import Path
from ..agents import AgentDirectory
from ..kernel import ROOT, JsonObject, OrgLayout
from ..services import ServiceCatalog
from ..settings import DEFAULT_CONFIG, OrgSettings
from ._protocols import OrgContext, OrgContexts

class NoOrgContext(OrgContext):
    """Plan time before the organization exists: the default settings, nothing taken, nothing to overlap."""

    def config(self) -> JsonObject:
        raise NotImplementedError('red: C-blueprint-1')

    def root(self) -> Path | None:
        raise NotImplementedError('red: C-blueprint-1')

    def exists(self, addr: str) -> bool:
        raise NotImplementedError('red: C-blueprint-1')

    def service_names(self) -> set[str]:
        raise NotImplementedError('red: C-blueprint-1')

class RuntimeOrgContext(OrgContext):

    def __init__(self, settings: OrgSettings, agents: AgentDirectory, services: ServiceCatalog, layout: OrgLayout) -> None:
        self._settings = settings
        self._agents = agents
        self._services = services
        self._layout = layout

    def config(self) -> JsonObject:
        raise NotImplementedError('red: C-blueprint-1')

    def root(self) -> Path | None:
        raise NotImplementedError('red: C-blueprint-1')

    def exists(self, addr: str) -> bool:
        raise NotImplementedError('red: C-blueprint-1')

    def service_names(self) -> set[str]:
        raise NotImplementedError('red: C-blueprint-1')

class PresentOrAbsentOrg(OrgContexts):

    def __init__(self, present: OrgContext, absent: OrgContext) -> None:
        self._present = present
        self._absent = absent

    def context(self, org_exists: bool) -> OrgContext:
        raise NotImplementedError('red: C-blueprint-1')
