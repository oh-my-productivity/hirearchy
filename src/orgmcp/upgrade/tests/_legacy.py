"""Access to what the upgrade package may not import from its tests: the legacy ``orgmcp.core``.

``upgrade`` is a feature: nothing under ``orgmcp/upgrade`` (its tests included) imports ``orgmcp.core`` (the layers contract). The
characterization tests need a real ``Org`` to call the old ``upgrade_rules(org)``, and reach the module by name at run time."""

from __future__ import annotations

import importlib
from typing import Any


def legacy(name: str) -> Any:
    """The module ``orgmcp.<name>``."""
    return importlib.import_module(f"orgmcp.{name}")
