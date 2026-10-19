"""The validator and its parts as the legacy module-level functions need them (not a port of the package).

The legacy functions are handed an ``Org`` (duck-typed) or none, and read the process they run in: the environment, ``scheduler.file_confinement``
(a patch point of the tests), the roles directory. They cannot take those from a runtime, so the composition root installs them once, when
``orgmcp.app`` is loaded (``install_legacy_parts``): a feature may not import the application package, nor the private modules of ``kernel``, ``kiro``
or ``services`` that make the real parts. Every legacy function and this module go away with the last caller (E3)."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..kernel import Environment
from ..kiro import ConfinementPolicy
from ..services import ContractNormalizer
from ._access import PolicyAccessReport
from ._budgeting import BudgetPlanner
from ._files import FsTextFiles
from ._host import HostOrgContext, OrgFacts
from ._loader import YamlBlueprintLoader
from ._org import NoOrgContext, PresentOrAbsentOrg
from ._pathcheck import RootedPathChecker
from ._protocols import AccessReport, AgentResolution, BudgetPlanning, OrgContext, WorkspaceRoots
from ._resolver import AgentResolver
from ._roles import PackagedRoleLibrary
from ._roots import EnvironmentWorkspaceRoots
from ._service_rules import ServiceBlueprintRules
from ._validator import RuleBlueprintValidator
from .api import BlueprintLoader, BlueprintValidator, RoleLibrary


@dataclass(frozen=True)
class LegacyParts:
    """What a legacy function works with, whether it is given an ``Org`` or none."""

    environment: Environment
    confinement_policy: ConfinementPolicy
    contract_normalizer: ContractNormalizer
    roles_dir: Path  # ``orgmcp/roles`` (package data): the wiring says where it is


_installed: LegacyParts | None = None


def install_legacy_parts(parts: LegacyParts) -> None:
    """Called by ``orgmcp.app`` when it is loaded."""
    global _installed
    _installed = parts


def legacy_parts() -> LegacyParts:
    """The parts in force; ``RuntimeError`` when ``orgmcp.app`` has not been loaded."""
    if _installed is None:
        raise RuntimeError("orgmcp.app is not loaded: the parts of the legacy blueprint functions are not installed")
    return _installed


@dataclass(frozen=True)
class Assembly:
    """The classes of the package made over the legacy parts and over the ``Org`` a legacy function was given (or none)."""

    roles: RoleLibrary
    loader: BlueprintLoader
    roots: WorkspaceRoots
    resolver: AgentResolution
    budgets: BudgetPlanning
    access: AccessReport
    org: OrgContext  # the organization given, or the defaults of plan time before there is one
    validator: BlueprintValidator


def assembly_of(org: OrgFacts | None) -> Assembly:
    parts = legacy_parts()
    context: OrgContext = HostOrgContext(org) if org is not None else NoOrgContext()
    roles = PackagedRoleLibrary(parts.roles_dir)
    paths = RootedPathChecker(parts.environment)
    roots = EnvironmentWorkspaceRoots(parts.environment, lambda: Path(tempfile.gettempdir()))
    resolver = AgentResolver(roles, paths)
    budgets = BudgetPlanner()
    access = PolicyAccessReport(parts.confinement_policy)
    services = ServiceBlueprintRules(parts.contract_normalizer, paths, budgets)
    validator = RuleBlueprintValidator(resolver, paths, budgets, access, services, roots, PresentOrAbsentOrg(context, NoOrgContext()))
    return Assembly(roles, YamlBlueprintLoader(FsTextFiles()), roots, resolver, budgets, access, context, validator)
