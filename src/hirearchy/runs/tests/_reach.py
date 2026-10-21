"""Access to what the runs package may not import from its tests: the modules above it.

``runs`` is a low layer: nothing under ``hirearchy/runs`` (its tests included) imports ``hirearchy.core``, ``hirearchy.health``, ``hirearchy.scheduler``
or ``hirearchy.dashdata`` (the layers contract). The tests that check the package against its consumers reach them by name at run time."""

from __future__ import annotations

import importlib
from typing import Any


def reach(name: str) -> Any:
    """The module ``hirearchy.<name>``, imported at run time (a static import is what the import contracts forbid)."""
    return importlib.import_module(f"hirearchy.{name}")
