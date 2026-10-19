"""Runtime fields of the composition root itself: the organization root and the process resources.

It also hands ``runtime.py`` the base that makes every field of every part lazy (``LazyPorts``, see ``_lazy.py``): ``runtime.py`` imports
only the parts, so the mechanism comes to it through the part of the composition root."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ._lazy import LazyPorts
from ._resources import ProcessResources

__all__ = ["Fields", "LazyPorts", "NOT_A_FIELD", "STEP"]

STEP: str | None = None
NOT_A_FIELD: dict[str, str] = {}


@dataclass(frozen=True)
class Fields:
    root: Path
    resources: ProcessResources
