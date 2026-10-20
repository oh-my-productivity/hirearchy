"""Runtime fields of ``access`` (ARCHITECTURE.md 3.16): one field per port that ``wire_access.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..access import AccessScopes, AuthorityPolicy, ModelResolver, ToolNaming

STEP: str | None = "B-access"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    access_scopes: AccessScopes
    authority_policy: AuthorityPolicy
    tool_naming: ToolNaming
    model_resolver: ModelResolver
