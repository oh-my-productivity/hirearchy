"""The parts of ``OrgRuntime``: one ``orgmcp.app.fields_<pkg>`` module per package (ARCHITECTURE.md 9.2), discovered, not listed."""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from types import ModuleType

import orgmcp.app

APP_DIR = Path(orgmcp.app.__file__).resolve().parent


def names(prefix: str) -> list[str]:
    """The ``<pkg>`` of every ``orgmcp/app/<prefix>_<pkg>.py``, sorted."""
    return sorted(m.name[len(prefix) + 1:] for m in pkgutil.iter_modules([str(APP_DIR)]) if m.name.startswith(prefix + "_"))


def part_names() -> list[str]:
    return names("fields")


def part(name: str) -> ModuleType:
    return importlib.import_module(f"orgmcp.app.fields_{name}")


def parts() -> dict[str, ModuleType]:
    return {name: part(name) for name in part_names()}


def done_steps() -> set[str]:
    """The steps that have filled a part (``STEP = "<step>"`` in its ``fields_<pkg>.py``)."""
    return {step for module in parts().values() if (step := getattr(module, "STEP", None))}


def not_a_field() -> dict[str, str]:
    """Every port that a step declared not to be a runtime field, with the reason (``NOT_A_FIELD`` of its part)."""
    merged: dict[str, str] = {}
    for module in parts().values():
        merged.update(getattr(module, "NOT_A_FIELD", {}))
    return merged
