"""The validator and its parts as the legacy module-level functions need them (not a port of the package).

The legacy functions are handed an ``Org`` (duck-typed) or none, and read the process they run in: the environment, ``scheduler.file_confinement``
(a patch point of the tests), the roles directory. They cannot take those from a runtime, so the composition root installs them once, when
``orgmcp.app`` is loaded (``install_legacy_parts``): a feature may not import the application package, nor the private modules of ``kernel``, ``kiro``
or ``services`` that make the real parts. Every legacy function and this module go away with the last caller (E3)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..kernel import Environment
from ..kiro import ConfinementPolicy
from ..services import ContractNormalizer
from ._host import OrgFacts
from ._protocols import AccessReport, AgentResolution, BudgetPlanning, OrgContext, PathChecking, WorkspaceRoots
from .api import BlueprintLoader, BlueprintValidator, RoleLibrary


@dataclass(frozen=True)
class LegacyParts:
    """What a legacy function works with, whether it is given an ``Org`` or none."""

    environment: Environment
    confinement_policy: ConfinementPolicy
    contract_normalizer: ContractNormalizer
    roles_dir: Path  # ``orgmcp/roles`` (package data): the wiring says where it is


def install_legacy_parts(parts: LegacyParts) -> None:
    """Called by ``orgmcp.app`` when it is loaded."""
    raise NotImplementedError("red: C-blueprint-1")


def legacy_parts() -> LegacyParts:
    raise NotImplementedError("red: C-blueprint-1")


@dataclass(frozen=True)
class Assembly:
    roles: RoleLibrary
    loader: BlueprintLoader
    paths: PathChecking
    roots: WorkspaceRoots
    resolver: AgentResolution
    budgets: BudgetPlanning
    access: AccessReport
    normalizer: ContractNormalizer
    org: OrgContext  # the organization given, or the defaults of plan time before there is one
    validator: BlueprintValidator


def assembly_of(org: OrgFacts | None) -> Assembly:
    raise NotImplementedError("red: C-blueprint-1")
