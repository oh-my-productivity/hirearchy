"""Runtime fields of ``bootstrap`` (ARCHITECTURE.md 3.33): one field per port that ``wire_bootstrap.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..bootstrap import OrgInitializer

STEP: str | None = "A-bootstrap"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    org_initializer: OrgInitializer
