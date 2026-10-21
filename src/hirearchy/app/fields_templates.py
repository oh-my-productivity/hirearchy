"""Runtime fields of ``templates`` (ARCHITECTURE.md 3.2): one field per port that ``wire_templates.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..templates import DocumentTemplates, Notices

STEP: str | None = "A-templates"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    document_templates: DocumentTemplates
    notices: Notices
