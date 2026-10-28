"""Runtime fields of ``blueprint`` (ARCHITECTURE.md 3.32): one field per port that ``wire_blueprint.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..blueprint import (
    BlueprintApplier,
    BlueprintExamples,
    BlueprintLoader,
    BlueprintValidator,
    ExtensionApplying,
    PlanIdentity,
    PlanRenderer,
    RoleLibrary,
    WorkspaceProvisioner,
)

STEP: str | None = "C-blueprint-2"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    role_library: RoleLibrary
    blueprint_loader: BlueprintLoader
    blueprint_validator: BlueprintValidator
    plan_renderer: PlanRenderer
    plan_identity: PlanIdentity
    blueprint_applier: BlueprintApplier
    extension_applier: ExtensionApplying
    blueprint_examples: BlueprintExamples
    workspace_provisioner: WorkspaceProvisioner
