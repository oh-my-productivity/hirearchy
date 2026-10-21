"""Runtime fields of ``locator`` (ARCHITECTURE.md 3.4): one field per port that ``wire_locator.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..locator import OrgLocator

STEP: str | None = "A-settings"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    locator: OrgLocator
