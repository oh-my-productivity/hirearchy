"""Providers of the ``blueprint`` ports (ARCHITECTURE.md 6.1).

The role templates stay in ``orgmcp/roles`` (package data, risk 8 of the architecture): the directory is found here, from the location of this
module, and handed to ``PackagedRoleLibrary``; the classes of ``blueprint`` never look at their own file name."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..agents import AgentDirectory
from ..blueprint import (
    BlueprintApplier,
    BlueprintExamples,
    BlueprintLoader,
    BlueprintValidator,
    PlanIdentity,
    PlanRenderer,
    RoleLibrary,
    WorkspaceProvisioner,
)
from ..blueprint._access import PolicyAccessReport
from ..blueprint._assembly import PlanParts, applier_over, plan_parts
from ..blueprint._budgeting import BudgetPlanner
from ..blueprint._examples import TemplateBlueprintExamples
from ..blueprint._files import FsTextFiles
from ..blueprint._loader import YamlBlueprintLoader
from ..blueprint._org import NoOrgContext, PresentOrAbsentOrg, RuntimeOrgContext
from ..blueprint._pathcheck import RootedPathChecker
from ..blueprint._provision import FsWorkspaceProvisioner
from ..blueprint._resolver import AgentResolver
from ..blueprint._roles import PackagedRoleLibrary
from ..blueprint._roots import EnvironmentWorkspaceRoots
from ..blueprint._service_rules import ServiceBlueprintRules
from ..blueprint._validator import RuleBlueprintValidator
from ..dispatch import TaskAssigner
from ..hierarchy import Hiring, Retirement
from ..kernel import Environment, OrgLayout
from ..kiro import ConfinementPolicy
from ..services import ContractNormalizer, ServiceCatalog, ServiceCommands
from ..settings import OrgSettings
from ..snapshots import OrgSnapshotter
from ._builder import Builder


def package_dir() -> Path:
    """The directory of the ``orgmcp`` package, from the location of this module (``orgmcp/app/wire_blueprint.py``: two levels up).

    Not from the location of the classes of ``blueprint`` (they moved one directory deeper than ``blueprint.py`` was): ``test_wire_blueprint`` pins
    the result to ``Path(orgmcp.__file__).parent`` so that moving this file cannot go unnoticed."""
    return Path(__file__).resolve().parent.parent


def roles_dir_of(package: Path) -> Path:
    """The role templates of the ``orgmcp`` package directory ``package``: ``roles/`` beside ``blueprint/`` (main: beside ``blueprint.py``)."""
    return package / "roles"


def roles_dir() -> Path:
    """``roles_dir_of`` the installed package."""
    return roles_dir_of(package_dir())


def temp_dir() -> Path:
    return Path(tempfile.gettempdir())


def register(b: Builder) -> None:
    b.provide(RoleLibrary, lambda b: PackagedRoleLibrary(roles_dir()))
    b.provide(BlueprintLoader, lambda b: YamlBlueprintLoader(FsTextFiles()))
    b.provide(BlueprintValidator, _validator)
    b.provide(PlanRenderer, lambda b: _plan(b).renderer)
    b.provide(PlanIdentity, lambda b: _plan(b).identity)
    b.provide(WorkspaceProvisioner, lambda b: FsWorkspaceProvisioner())
    b.provide(BlueprintExamples, lambda b: TemplateBlueprintExamples())
    b.provide(BlueprintApplier, _applier)


@dataclass(frozen=True)
class Checking:
    """The parts that check a blueprint, made over the ports of the runtime: the validator and the plan side are made of the same ones."""

    paths: RootedPathChecker
    budgets: BudgetPlanner
    access: PolicyAccessReport
    resolver: AgentResolver
    roots: EnvironmentWorkspaceRoots
    org: RuntimeOrgContext


def _checking(b: Builder) -> Checking:
    environment = b.get(Environment)
    paths = RootedPathChecker(environment)
    org = RuntimeOrgContext(b.get(OrgSettings), b.get(AgentDirectory), b.get(ServiceCatalog), b.get(OrgLayout))
    return Checking(
        paths, BudgetPlanner(), PolicyAccessReport(b.get(ConfinementPolicy)), AgentResolver(b.get(RoleLibrary), paths),
        EnvironmentWorkspaceRoots(environment, temp_dir), org,
    )


def _validator(b: Builder) -> BlueprintValidator:
    c = _checking(b)
    return RuleBlueprintValidator(
        c.resolver, c.paths, c.budgets, c.access, ServiceBlueprintRules(b.get(ContractNormalizer), c.paths, c.budgets), c.roots,
        PresentOrAbsentOrg(c.org, NoOrgContext()),
    )


def _plan(b: Builder) -> PlanParts:
    c = _checking(b)
    return plan_parts(b.get(BlueprintLoader), b.get(BlueprintValidator), c.resolver, c.roots, c.budgets, c.access, b.get(ContractNormalizer), c.org)


def _applier(b: Builder) -> BlueprintApplier:
    return applier_over(
        _plan(b), BudgetPlanner(), b.get(ContractNormalizer), b.get(Hiring), b.get(Retirement), b.get(AgentDirectory), b.get(ServiceCommands),
        b.get(TaskAssigner), b.get(OrgSnapshotter), b.get(WorkspaceProvisioner),
    )
