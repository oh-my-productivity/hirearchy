"""Access to what the eventlog package may not import from its tests: the modules above it.

``eventlog`` is a low layer: nothing under ``orgmcp/eventlog`` (its tests included) imports ``orgmcp.core`` or ``orgmcp.app`` (the layers
contract). The tests that check the package against the writer and the facade reach them by name at run time."""

from __future__ import annotations

import importlib
from typing import Any


def reach(name: str) -> Any:
    """The module ``orgmcp.<name>``, imported at run time (a static import is what the import contracts forbid)."""
    return importlib.import_module(f"orgmcp.{name}")
