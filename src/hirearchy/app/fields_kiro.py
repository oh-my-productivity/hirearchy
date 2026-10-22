"""Runtime fields of ``kiro`` (ARCHITECTURE.md 3.34): one field per port that ``wire_kiro.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..kiro import (
    ConfinementPolicy, KiroCli, KiroHomeAudit, KiroPlaces, KiroStateDirs, McpServerLocator, ProfileProvisioner, ProfileStore, RunCommandBuilder,
    RuntimeReadiness,
)

STEP: str | None = "B-kiro"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    confinement_policy: ConfinementPolicy
    profile_store: ProfileStore
    profile_provisioner: ProfileProvisioner
    mcp_locator: McpServerLocator
    run_command_builder: RunCommandBuilder
    kiro_places: KiroPlaces
    kiro_state_dirs: KiroStateDirs
    kiro_home_audit: KiroHomeAudit
    kiro_cli: KiroCli
    runtime_readiness: RuntimeReadiness
