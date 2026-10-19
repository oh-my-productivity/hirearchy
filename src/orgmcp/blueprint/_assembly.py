"""The validator and its parts as the legacy module-level functions need them (not a port of the package).

The legacy functions are handed an ``Org`` (duck-typed) or none, and read the process they run in: the environment, ``scheduler.file_confinement``
(a patch point of the tests), the roles directory. They cannot take those from a runtime, so the composition root installs them once, when
``orgmcp.app`` is loaded (``install_legacy_parts``): a feature may not import the application package, nor the private modules of ``kernel``, ``kiro``
or ``services`` that make the real parts. Every legacy function and this module go away with the last caller (E3)."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..agents import AgentDirectory
from ..dispatch import TaskAssigner
from ..hierarchy import Hiring, Retirement
from ..kernel import Environment
from ..kiro import ConfinementPolicy
from ..services import ContractNormalizer, ServiceCommands
from ..snapshots import OrgSnapshotter
from ._access import PolicyAccessReport
from ._accesswords import PlainAccessWords
from ._applier import HiringBlueprintApplier
from ._basis import ValidatedPlanBasis
from ._budgeting import BudgetPlanner
from ._charters import CharterWriter
from ._details import TextPlanDetails
from ._files import FsTextFiles
from ._firsttask import FirstTaskGiver
from ._host import HostOrgContext, OrgFacts, OrgWithPorts
from ._identity import HashPlanIdentity
from ._loader import YamlBlueprintLoader
from ._org import NoOrgContext, PresentOrAbsentOrg
from ._pathcheck import RootedPathChecker
from ._playbooks import StepsPlaybookWriter
from ._protocols import (
    AccessReport,
    AccessWording,
    AgentResolution,
    BudgetPlanning,
    Charters,
    OrgContext,
    PlanBasis,
    PlaybookWriting,
    PlanWords,
    WorkspaceRoots,
)
from ._provision import FsWorkspaceProvisioner
from ._render import TextPlanRenderer
from ._resolver import AgentResolver
from ._roles import PackagedRoleLibrary
from ._roots import EnvironmentWorkspaceRoots
from ._servicedef import PlaybookServiceDefiner
from ._service_rules import ServiceBlueprintRules
from ._team import CharterTeamBuilder
from ._undo import RetiringRollback
from ._userplan import TextUserPlan
from ._validator import RuleBlueprintValidator
from ._words import ServiceWords
from .api import BlueprintApplier, BlueprintLoader, BlueprintValidator, PlanIdentity, PlanRenderer, RoleLibrary, WorkspaceProvisioner


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
class PlanParts:
    """The classes that write the plan and the charters, made over the classes that check the blueprint."""

    basis: PlanBasis
    words: PlanWords
    playbooks: PlaybookWriting
    charters: Charters
    access_words: AccessWording
    identity: PlanIdentity
    renderer: PlanRenderer


def plan_parts(
    loader: BlueprintLoader, validator: BlueprintValidator, resolver: AgentResolution, roots: WorkspaceRoots, budgets: BudgetPlanning,
    access: AccessReport, normalizer: ContractNormalizer, org: OrgContext,
) -> PlanParts:
    """The plan side of the package over the given parts: the one place that says how its classes are put together."""
    basis = ValidatedPlanBasis(validator, resolver, roots, org)
    words, playbooks, identity = ServiceWords(normalizer), StepsPlaybookWriter(budgets), HashPlanIdentity()
    access_words = PlainAccessWords(access)
    details = TextPlanDetails(basis, budgets, access, playbooks, words)
    renderer = TextPlanRenderer(loader, basis, details, TextUserPlan(basis, budgets, access_words, words), identity)
    return PlanParts(basis, words, playbooks, CharterWriter(), access_words, identity, renderer)


def applier_over(
    plan: PlanParts, budgets: BudgetPlanning, normalizer: ContractNormalizer, hiring: Hiring, retirement: Retirement, agents: AgentDirectory,
    commands: ServiceCommands, tasks: TaskAssigner, snapshots: OrgSnapshotter, provisioner: WorkspaceProvisioner,
) -> BlueprintApplier:
    """The applier over the given plan and the ports it builds with."""
    return HiringBlueprintApplier(
        plan.basis, budgets, CharterTeamBuilder(hiring, plan.charters, provisioner),
        PlaybookServiceDefiner(commands, normalizer, plan.playbooks, budgets), FirstTaskGiver(tasks, commands),
        RetiringRollback(agents, retirement, provisioner), snapshots,
    )


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
    plan: PlanParts


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
    loader = YamlBlueprintLoader(FsTextFiles())
    plan = plan_parts(loader, validator, resolver, roots, budgets, access, parts.contract_normalizer, context)
    return Assembly(roles, loader, roots, resolver, budgets, access, context, validator, plan)


def applier_of(org: OrgWithPorts) -> BlueprintApplier:
    """The applier of a legacy ``apply``: the plan side over the ``Org`` given, and the ports that ``Org`` has *now* (``org.runtime``)."""
    a, ports = assembly_of(org), org.runtime
    return applier_over(
        a.plan, a.budgets, legacy_parts().contract_normalizer, ports.hiring, ports.retirement, ports.agents, ports.service_commands,
        ports.task_assigner, ports.snapshotter, FsWorkspaceProvisioner(),
    )
