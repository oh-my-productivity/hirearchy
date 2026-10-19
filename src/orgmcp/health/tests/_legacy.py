"""Access to what the health package may not import from its tests: the legacy modules (the facade ``orgmcp.core`` among them).

``health`` is a feature: nothing under ``orgmcp/health`` (its tests included) imports ``orgmcp.core`` or the other legacy modules (the layers
contract). The characterization tests build their organizations with the legacy ``Org`` and compare the package with the legacy module
functions, so they reach both by name at run time.
"""

from __future__ import annotations

import importlib
from typing import Any


def legacy(name: str) -> Any:
    """The module ``orgmcp.<name>``."""
    return importlib.import_module(f"orgmcp.{name}")
