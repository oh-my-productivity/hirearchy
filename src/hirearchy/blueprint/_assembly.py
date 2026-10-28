"""The classes of the plan side and of the applier, put together from the ports they are made of: the one place that says how they are assembled.

``hirearchy.app`` (``wire_blueprint``, ``wire_cli``, ``wire_mcp_server``) and the fakes of the package (``testing``) build them through these two functions: a
feature may not import the application package, nor the private modules of ``kernel``, ``kiro`` or ``services`` that make the real ports."""

from __future__ import annotations

from dataclasses import dataclass

from ..agents import AgentDirectory, AgentRegistry
from ..dispatch import MessageSender, TaskAssigner
from ..hierarchy import Hiring, Retirement
from ..kernel import EventSink
from ..services import ContractNormalizer, ServiceCommands
from ..settings import OrgLimits
from ..snapshots import OrgSnapshotter
from ._accesswords import PlainAccessWords
from ._applier import HiringBlueprintApplier
from ._basis import ValidatedPlanBasis
from ._charters import CharterWriter
from ._details import TextPlanDetails
from ._extension import ExtensionResolver
from ._extension_apply import ExtensionApplier
from ._extension_org import Reads
from ._extension_plan import TextExtensionPlan
from ._fingerprint import OrgFingerprint
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
from ._undo import ExtensionUndo, RetiringRollback
from ._userplan import TextUserPlan
from ._words import ServiceWords
from .api import BlueprintApplier, BlueprintLoader, BlueprintValidator, ExtensionApplying, PlanIdentity, PlanRenderer, WorkspaceProvisioner


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
    access: AccessReport, normalizer: ContractNormalizer, org: OrgContext, reads: Reads | None = None,
) -> PlanParts:
    """The plan side of the package over the given parts: the one place that says how its classes are put together. ``reads``: what the rules of an
    extension read the organization through (without it a plan is for a full blueprint only, and an extension's plan id covers the blueprint alone)."""
    basis = ValidatedPlanBasis(validator, resolver, roots, org)
    fingerprint = OrgFingerprint(reads) if reads is not None else None
    words, playbooks, identity = ServiceWords(normalizer), StepsPlaybookWriter(budgets), HashPlanIdentity(fingerprint)
    access_words, charters = PlainAccessWords(access), CharterWriter()
    details = TextPlanDetails(basis, budgets, access, playbooks, words)
    extensions = (
        TextExtensionPlan(ExtensionResolver(reads), reads, access_words, words, charters, identity, fingerprint)
        if reads is not None and fingerprint is not None else None
    )
    renderer = TextPlanRenderer(loader, basis, details, TextUserPlan(basis, budgets, access_words, words, org), identity, extensions)
    return PlanParts(basis, words, playbooks, charters, access_words, identity, renderer)


def applier_over(
    plan: PlanParts, budgets: BudgetPlanning, normalizer: ContractNormalizer, hiring: Hiring, retirement: Retirement, agents: AgentDirectory,
    commands: ServiceCommands, tasks: TaskAssigner, snapshots: OrgSnapshotter, provisioner: WorkspaceProvisioner,
) -> BlueprintApplier:
    """The applier over the given plan and the ports it builds with."""
    return HiringBlueprintApplier(
        plan.basis, budgets, CharterTeamBuilder(hiring, plan.charters, provisioner),
        PlaybookServiceDefiner(commands, normalizer, plan.playbooks, budgets), FirstTaskGiver(tasks, commands),
        RetiringRollback(agents, retirement, provisioner), snapshots, plan.identity,
    )


def extension_applier_over(
    plan: PlanParts, reads: Reads, normalizer: ContractNormalizer, hiring: Hiring, retirement: Retirement, registry: AgentRegistry, commands: ServiceCommands,
    limits: OrgLimits, sender: MessageSender, snapshots: OrgSnapshotter, events: EventSink,
) -> ExtensionApplying:
    """The applier of an extension of the current organization over the given plan, the ports it writes through and what its rules read."""
    return ExtensionApplier(
        reads, ExtensionResolver(reads), plan.identity, plan.charters, plan.playbooks, normalizer, hiring, retirement, registry, commands, limits, sender,
        ExtensionUndo(reads.agents, retirement, registry, commands, limits), snapshots, events,
    )
