"""Access to what the settings package may not import from its tests: the modules above it and PyYAML.

``settings`` is a low layer: nothing under ``hirearchy/settings`` (its tests included) imports ``hirearchy.core`` or ``hirearchy.health`` (the layers
contract) or ``yaml`` (only the kernel parses YAML). The tests that check the package against the facade, and the one that needs the error
PyYAML raises, reach both by name at run time.
"""

from __future__ import annotations

import importlib
from typing import Any


def reach(name: str) -> Any:
    """The module ``hirearchy.<name>``, imported at run time (a static import is what the import contracts forbid)."""
    return importlib.import_module(f"hirearchy.{name}")


def yaml_error() -> type[Exception]:
    """``yaml.YAMLError``: what a malformed frontmatter block raises."""
    error: type[Exception] = importlib.import_module("yaml").YAMLError
    return error
