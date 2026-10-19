"""Loads ``tools/relocate_tests.py`` (dev tooling, not part of the package) for the tests that check the manifest and the mover."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from .paths import REPO

TOOL = REPO / "tools" / "relocate_tests.py"
MANIFEST = Path(__file__).with_name("relocation.yaml")


def load() -> ModuleType:
    """The tool module, imported by path (``tools/`` is not a package of ``orgmcp`` and is not on ``sys.path``)."""
    if "relocate_tests" in sys.modules:
        return sys.modules["relocate_tests"]
    spec = importlib.util.spec_from_file_location("relocate_tests", TOOL)
    assert spec is not None and spec.loader is not None, f"{TOOL} is missing"
    module = importlib.util.module_from_spec(spec)
    sys.modules["relocate_tests"] = module  # dataclasses look their module up here
    spec.loader.exec_module(module)
    return module
