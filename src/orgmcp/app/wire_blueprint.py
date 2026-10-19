"""Providers of the ``blueprint`` ports (ARCHITECTURE.md 6.1), and the parts the legacy module-level functions of ``blueprint`` work with.

The role templates stay in ``orgmcp/roles`` (package data, risk 8 of the architecture): the directory is found here, from the location of this
module, and handed to ``PackagedRoleLibrary``; the classes of ``blueprint`` never look at their own file name.

The legacy functions (``validate``, ``get_role``, ...) take an optional ``Org`` and read the process they run in; they cannot take their parts from
a runtime, so ``legacy_parts`` makes them once and ``fields_blueprint`` installs them when the application package is loaded. They go away with
the last legacy caller (E3)."""

from __future__ import annotations

import importlib
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from ..agents import AgentDirectory
from ..blueprint import BlueprintLoader, BlueprintValidator, RoleLibrary
from ..blueprint._access import PolicyAccessReport
from ..blueprint._assembly import LegacyParts
from ..blueprint._assembly import install_legacy_parts as install
from ..blueprint._budgeting import BudgetPlanner
from ..blueprint._files import FsTextFiles
from ..blueprint._loader import YamlBlueprintLoader
from ..blueprint._org import NoOrgContext, PresentOrAbsentOrg, RuntimeOrgContext
from ..blueprint._pathcheck import RootedPathChecker
from ..blueprint._resolver import AgentResolver
from ..blueprint._roles import PackagedRoleLibrary
from ..blueprint._roots import EnvironmentWorkspaceRoots
from ..blueprint._service_rules import ServiceBlueprintRules
from ..blueprint._validator import RuleBlueprintValidator
from ..kernel import Environment, OrgLayout
from ..kernel._system import OsEnvironment
from ..kiro import ConfinementPolicy
from ..services import ContractNormalizer, ServiceCatalog
from ..services._normalizer import TextContractNormalizer
from ..settings import OrgSettings
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


class PatchPointConfinementPolicy(ConfinementPolicy):
    """A policy that is a function: whatever ``scheduler.file_confinement`` is when the plan asks what the built-in ``read`` may open.

    The flat module asked the scheduler's function at each call, and tests replace it; this keeps that patch point for the legacy functions."""

    def file_confinement(
        self, org_root: Path, tools: Sequence[str], workspace: Path | None, inputs: Sequence[Path]
    ) -> tuple[list[str], dict[str, object]]:
        scheduler = sys.modules.get("orgmcp.scheduler") or importlib.import_module("orgmcp.scheduler")  # it imports this package: looked up late
        return cast("tuple[list[str], dict[str, object]]", scheduler.file_confinement(org_root, list(tools), workspace, list(inputs)))


def legacy_parts() -> LegacyParts:
    """The process the legacy functions of ``blueprint`` run in: the real environment, the scheduler's confinement policy, the roles directory."""
    return LegacyParts(OsEnvironment(), PatchPointConfinementPolicy(), TextContractNormalizer(), roles_dir())


def install_legacy_parts() -> None:
    """Hand the legacy parts to ``blueprint``; ``fields_blueprint`` calls this when the application package is loaded."""
    install(legacy_parts())


def register(b: Builder) -> None:
    b.provide(RoleLibrary, lambda b: PackagedRoleLibrary(roles_dir()))
    b.provide(BlueprintLoader, lambda b: YamlBlueprintLoader(FsTextFiles()))
    b.provide(BlueprintValidator, _validator)


def _validator(b: Builder) -> BlueprintValidator:
    environment = b.get(Environment)
    paths = RootedPathChecker(environment)
    budgets = BudgetPlanner()
    org = RuntimeOrgContext(b.get(OrgSettings), b.get(AgentDirectory), b.get(ServiceCatalog), b.get(OrgLayout))
    return RuleBlueprintValidator(
        AgentResolver(b.get(RoleLibrary), paths), paths, budgets, PolicyAccessReport(b.get(ConfinementPolicy)),
        ServiceBlueprintRules(b.get(ContractNormalizer), paths, budgets), EnvironmentWorkspaceRoots(environment, temp_dir),
        PresentOrAbsentOrg(org, NoOrgContext()),
    )
