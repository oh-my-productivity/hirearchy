"""Runtime fields of ``overview`` (ARCHITECTURE.md 3.23): one field per port that ``wire_overview.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..overview import OrgTree

STEP: str | None = "C-overview"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    org_tree: OrgTree
