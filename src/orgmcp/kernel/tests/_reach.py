"""Access to the modules above the kernel from the kernel's tests without a static import.

The kernel is the bottom layer: nothing under ``orgmcp/kernel`` (its tests included) may import an upper module statically
(``test_independence.py`` enforces it). The tests that check the kernel against ``orgmcp.core`` and the mail parser reach them by name at run time."""

from __future__ import annotations

import importlib
from typing import Any


def reach(name: str) -> Any:
    """The module ``orgmcp.<name>``, imported at run time (a static import is what the import contracts forbid)."""
    return importlib.import_module(f"orgmcp.{name}")
