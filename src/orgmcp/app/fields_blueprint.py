"""Runtime fields of ``blueprint`` (ARCHITECTURE.md 3.32): one field per port that ``wire_blueprint.py`` builds.

Importing this part also installs the parts of the legacy functions of ``blueprint`` (``wire_blueprint.install_legacy_parts``): ``runtime.py`` imports
every part when the application package is loaded, and a legacy function (``blueprint.validate(bp)``, with no ``Org`` at hand) needs them from then on.
This goes with the legacy functions (E3)."""

from __future__ import annotations

from dataclasses import dataclass

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
from . import wire_blueprint

STEP: str | None = "C-blueprint-2"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)

wire_blueprint.install_legacy_parts()


@dataclass(frozen=True)
class Fields:
    role_library: RoleLibrary
    blueprint_loader: BlueprintLoader
    blueprint_validator: BlueprintValidator
    plan_renderer: PlanRenderer
    plan_identity: PlanIdentity
    blueprint_applier: BlueprintApplier
    blueprint_examples: BlueprintExamples
    workspace_provisioner: WorkspaceProvisioner
