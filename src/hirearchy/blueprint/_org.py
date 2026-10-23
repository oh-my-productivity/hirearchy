"""The organization a blueprint is planned against: the real one, or none yet."""

from __future__ import annotations

from pathlib import Path

from ..agents import AgentDirectory
from ..kernel import ROOT, JsonObject, OrgLayout
from ..services import ServiceCatalog
from ..settings import DEFAULT_CONFIG, OrgSettings, readable_config
from ._protocols import OrgContext, OrgContexts


class NoOrgContext(OrgContext):
    """Plan time before the organization exists: the default settings, nothing taken, nothing to overlap."""

    def config(self) -> JsonObject:
        return dict(DEFAULT_CONFIG)

    def root(self) -> Path | None:
        return None

    def exists(self, addr: str) -> bool:
        return False

    def service_names(self) -> set[str]:
        return set()


class RuntimeOrgContext(OrgContext):
    def __init__(self, settings: OrgSettings, agents: AgentDirectory, services: ServiceCatalog, layout: OrgLayout) -> None:
        self._settings = settings
        self._agents = agents
        self._services = services
        self._layout = layout

    def config(self) -> JsonObject:
        return readable_config(self._settings)  # a plan is refused in plain words when ORG.md does not parse

    def root(self) -> Path | None:
        return self._layout.root

    def exists(self, addr: str) -> bool:
        return self._agents.exists(addr)

    def service_names(self) -> set[str]:
        return {n for kid in self._agents.children(ROOT) for n in self._services.service_names(kid)}


class PresentOrAbsentOrg(OrgContexts):
    def __init__(self, present: OrgContext, absent: OrgContext) -> None:
        self._present = present
        self._absent = absent

    def context(self, org_exists: bool) -> OrgContext:
        return self._present if org_exists else self._absent
