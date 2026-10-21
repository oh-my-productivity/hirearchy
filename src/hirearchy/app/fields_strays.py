"""Runtime fields of ``strays`` (ARCHITECTURE.md 3.13): one field per port that ``wire_strays.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..strays import StrayProbe, StrayRegistry

STEP: str | None = "B-strays"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    stray_probe: StrayProbe
    stray_registry: StrayRegistry
