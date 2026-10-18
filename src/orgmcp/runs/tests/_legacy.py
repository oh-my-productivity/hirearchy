"""Access to what the runs package may not import from its tests: the legacy modules.

``runs`` is a low layer: nothing under ``orgmcp/runs`` (its tests included) imports ``orgmcp.core``, ``orgmcp.health``, ``orgmcp.observe``,
``orgmcp.scheduler`` or ``orgmcp.dashboard_data`` (the layers contract). The characterization tests compare the package with those
modules, so they reach them by name at run time.
"""

from __future__ import annotations

import importlib
from typing import Any


def legacy(name: str) -> Any:
    """The module ``orgmcp.<name>``."""
    return importlib.import_module(f"orgmcp.{name}")
