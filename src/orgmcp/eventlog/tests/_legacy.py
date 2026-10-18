"""Access to what the eventlog package may not import from its tests: the legacy modules that still exist.

``eventlog`` is a low layer: nothing under ``orgmcp/eventlog`` (its tests included) imports ``orgmcp.core``, ``orgmcp.telemetry`` or
``orgmcp.observe`` (the layers contract). The characterization tests compare the package with those modules, and reach them by
name at run time.
"""

from __future__ import annotations

import importlib
from typing import Any


def legacy(name: str) -> Any:
    """The module ``orgmcp.<name>``."""
    return importlib.import_module(f"orgmcp.{name}")
