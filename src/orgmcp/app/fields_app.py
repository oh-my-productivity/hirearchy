"""Runtime fields of the composition root itself: the organization root and the process resources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ._resources import ProcessResources

STEP: str | None = None
NOT_A_FIELD: dict[str, str] = {}


@dataclass(frozen=True)
class Fields:
    root: Path
    resources: ProcessResources
