"""Access to the legacy modules from the kernel's tests without a static import.

The kernel is the bottom layer: nothing under ``orgmcp/kernel`` (its tests included) may import an upper module
statically (``test_independence.py`` enforces it). The oracle and compatibility tests compare the kernel with the legacy
modules that still exist, so they reach them by name at run time.
"""

from __future__ import annotations

import importlib
from typing import Any


def legacy(name: str) -> Any:
    """The module ``orgmcp.<name>``."""
    return importlib.import_module(f"orgmcp.{name}")
