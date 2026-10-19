"""Runtime fields of ``delivery`` (ARCHITECTURE.md 3.15): one field per port that ``wire_delivery.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..delivery import MessageDelivery

STEP: str | None = "B-delivery"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    delivery: MessageDelivery
