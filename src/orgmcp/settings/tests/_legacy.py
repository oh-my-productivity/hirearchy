"""Access to what the settings package may not import from its tests: the legacy modules and PyYAML.

``settings`` is a low layer: nothing under ``orgmcp/settings`` (its tests included) imports ``orgmcp.core``, ``orgmcp.health`` or
``orgmcp.dashboard_data`` (the layers contract) or ``yaml`` (only the kernel parses YAML). The characterization tests compare the
package with the legacy modules that still exist, and need the error PyYAML raises, so they reach both by name at run time.
"""

from __future__ import annotations

import importlib
from typing import Any


def legacy(name: str) -> Any:
    """The module ``orgmcp.<name>``."""
    return importlib.import_module(f"orgmcp.{name}")


def yaml_error() -> type[Exception]:
    """``yaml.YAMLError``: what a malformed frontmatter block raises."""
    error: type[Exception] = importlib.import_module("yaml").YAMLError
    return error
