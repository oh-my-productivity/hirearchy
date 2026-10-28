"""Providers of the ``blueprint`` ports (ARCHITECTURE.md 6.1).

The role templates stay in ``hirearchy/roles`` (package data, risk 8 of the architecture): the directory is found here, from the location of this
module, and handed to ``PackagedRoleLibrary``; the classes of ``blueprint`` never look at their own file name."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..agents import AgentDirectory, CharterReader, RetiredArchive
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
from ..blueprint._extension_org import Reads
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
from ..mail import MailboxReader
from ..services import ContractNormalizer, ServiceCatalog, ServiceCommands, ServiceEvidence
from ..services._continue import RecordedContinuations
from ..services._places import OrgServicePlaces
from ..services._store import OsServiceFiles
from ..settings import OrgSettings
from ..snapshots import OrgSnapshotter
from ._builder import Builder
from ._continued_criteria import RecordedContinuedCriteria
from ._root_tasks import MailRootTasks


def package_dir() -> Path:
    """The directory of the ``hirearchy`` package, from the location of this module (``hirearchy/app/wire_blueprint.py``: two levels up).

    Not from the location of the classes of ``blueprint`` (they moved one directory deeper than ``blueprint.py`` was): ``test_wire_blueprint`` pins
    the result to ``Path(hirearchy.__file__).parent`` so that moving this file cannot go unnoticed."""
    return Path(__file__).resolve().parent.parent


def roles_dir_of(package: Path) -> Path:
    """The role templates of the ``hirearchy`` package directory ``package``: ``roles/`` beside ``blueprint/`` (main: beside ``blueprint.py``)."""
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


def _reads(b: Builder) -> Reads:
    """What the rules of an extension read the organization through: the real ports of the runtime."""
    c = _checking(b)
    places, mail = OrgServicePlaces(b.get(OrgLayout)), b.get(MailboxReader)
    continued = RecordedContinuedCriteria(RecordedContinuations(places, b.get(RetiredArchive), mail, OsServiceFiles()))
    return Reads(
        c.org, b.get(AgentDirectory), b.get(CharterReader), b.get(RoleLibrary), c.resolver, c.roots, b.get(ServiceCatalog), b.get(ServiceEvidence), c.budgets,
        ServiceBlueprintRules(b.get(ContractNormalizer), c.paths, c.budgets), MailRootTasks(mail), continued,
    )


def _plan(b: Builder) -> PlanParts:
    c = _checking(b)
    return plan_parts(
        b.get(BlueprintLoader), b.get(BlueprintValidator), c.resolver, c.roots, c.budgets, c.access, b.get(ContractNormalizer), c.org, _reads(b),
    )


def _applier(b: Builder) -> BlueprintApplier:
    return applier_over(
        _plan(b), BudgetPlanner(), b.get(ContractNormalizer), b.get(Hiring), b.get(Retirement), b.get(AgentDirectory), b.get(ServiceCommands),
        b.get(TaskAssigner), b.get(OrgSnapshotter), b.get(WorkspaceProvisioner),
    )
