"""Runtime fields of the ``scheduler`` entry point (ARCHITECTURE.md 6.2: ``scheduler_factory``)."""

from __future__ import annotations

from dataclasses import dataclass

STEP: str | None = None  # set to the step's name when the step fills this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    """No field yet: the step that gives the package its ports adds them here."""
