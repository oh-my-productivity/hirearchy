"""Runtime fields of ``settings`` (ARCHITECTURE.md 3.3): one field per port that ``wire_settings.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..settings import EventSwitch, OrgDocumentStore, OrgSettings

STEP: str | None = "A-settings"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    settings: OrgSettings
    documents: OrgDocumentStore
    event_switch: EventSwitch
