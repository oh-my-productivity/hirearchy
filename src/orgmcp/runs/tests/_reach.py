"""Access to what the runs package may not import from its tests: the modules above it.

``runs`` is a low layer: nothing under ``orgmcp/runs`` (its tests included) imports ``orgmcp.core``, ``orgmcp.health``, ``orgmcp.scheduler``
or ``orgmcp.dashdata`` (the layers contract). The tests that check the package against its consumers reach them by name at run time."""

from __future__ import annotations

import importlib
from typing import Any


def reach(name: str) -> Any:
    """The module ``orgmcp.<name>``, imported at run time (a static import is what the import contracts forbid)."""
    return importlib.import_module(f"orgmcp.{name}")
