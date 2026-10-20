"""Runtime fields of ``progress`` (ARCHITECTURE.md 3.30): one field per port that ``wire_progress.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..progress import ProgressReporter

STEP: str | None = "C-progress"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    progress_reporter: ProgressReporter
