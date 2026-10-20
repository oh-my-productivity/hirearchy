"""The classes of the plan side and of the applier, put together from the ports they are made of: the one place that says how they are assembled.

``orgmcp.app`` (``wire_blueprint``, ``wire_cli``, ``wire_mcp_server``) and the fakes of the package (``testing``) build them through these two functions: a
feature may not import the application package, nor the private modules of ``kernel``, ``kiro`` or ``services`` that make the real ports."""

from __future__ import annotations

from dataclasses import dataclass

from ..agents import AgentDirectory
from ..dispatch import TaskAssigner
from ..hierarchy import Hiring, Retirement
from ..services import ContractNormalizer, ServiceCommands
from ..snapshots import OrgSnapshotter
from ._accesswords import PlainAccessWords
from ._applier import HiringBlueprintApplier
from ._basis import ValidatedPlanBasis
from ._charters import CharterWriter
from ._details import TextPlanDetails
from ._firsttask import FirstTaskGiver
from ._identity import HashPlanIdentity
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
from ._render import TextPlanRenderer
from ._servicedef import PlaybookServiceDefiner
from ._team import CharterTeamBuilder
from ._undo import RetiringRollback
from ._userplan import TextUserPlan
from ._words import ServiceWords
from .api import BlueprintApplier, BlueprintLoader, BlueprintValidator, PlanIdentity, PlanRenderer, WorkspaceProvisioner


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
