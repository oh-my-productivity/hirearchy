"""Access to what the agents package may not import from its tests: the legacy modules (the layers contract)."""

from __future__ import annotations

import importlib
from typing import Any


def legacy(name: str) -> Any:
    """The module ``orgmcp.<name>``."""
    return importlib.import_module(f"orgmcp.{name}")
