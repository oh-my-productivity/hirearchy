"""``OrgRuntime`` is composed of one part per package, so that two steps never edit the same line (ARCHITECTURE.md 9.2).

A step that gives its package ports edits only ``app/fields_<pkg>.py`` (the fields), ``app/wire_<pkg>.py`` (the providers) and its own tests;
``runtime.py``, ``wiring.py`` and the done-set of ``test_runtime_fields`` are never edited by a step.
"""

from __future__ import annotations

import ast
import dataclasses
import typing

import pytest

from hirearchy.app.runtime import OrgRuntime

from . import _parts
from ._parts import APP_DIR

NOT_FEATURES = ["kernel", "scheduler", "app"]  # the kernel, an entry point and the composition root itself


def test_the_parts_are_discovered() -> None:
    names = _parts.part_names()
    assert {"app", "kernel", "settings", "locator", "templates", "snapshots", "processes", "mail", "budget", "dashdata"} <= set(names)
    assert len(names) >= 38


def test_every_package_with_providers_has_a_part() -> None:
    assert set(_parts.names("wire")) <= set(_parts.part_names())


def test_every_part_is_a_frozen_dataclass_named_fields() -> None:
    for name, module in _parts.parts().items():
        fields = getattr(module, "Fields", None)
        assert dataclasses.is_dataclass(fields), name
        assert fields.__dataclass_params__.frozen, name  # type: ignore[union-attr]
        assert hasattr(module, "STEP") and isinstance(module.NOT_A_FIELD, dict), name


def test_the_runtime_is_composed_of_every_part() -> None:
    bases = set(OrgRuntime.__mro__)
    assert [name for name, module in _parts.parts().items() if module.Fields not in bases] == []


def test_runtime_py_declares_no_field_and_imports_only_its_parts() -> None:
    tree = ast.parse((APP_DIR / "runtime.py").read_text(encoding="utf-8"))
    runtime = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "OrgRuntime")
    assert [n for n in runtime.body if isinstance(n, ast.AnnAssign)] == []  # no field of its own
    imported = {alias.name for node in tree.body if isinstance(node, ast.ImportFrom) and node.level == 1 for alias in node.names}
    assert all(name.startswith("fields_") for name in imported), imported


def test_the_runtime_has_exactly_the_fields_of_its_parts() -> None:
    declared = [name for module in _parts.parts().values() for name in typing.get_type_hints(module.Fields)]
    assert sorted(f.name for f in dataclasses.fields(OrgRuntime)) == sorted(declared)


def test_no_field_is_declared_by_two_parts() -> None:
    owners: dict[str, list[str]] = {}
    for pkg, module in _parts.parts().items():
        for field in typing.get_type_hints(module.Fields):
            owners.setdefault(field, []).append(pkg)
    assert {field: pkgs for field, pkgs in owners.items() if len(pkgs) > 1} == {}


def test_a_part_declares_only_ports_of_its_own_package() -> None:
    wrong = []
    for pkg, module in _parts.parts().items():
        if pkg in ("app", "scheduler"):
            continue
        for field, hint in typing.get_type_hints(module.Fields).items():
            if isinstance(hint, type) and not hint.__module__.startswith(f"hirearchy.{pkg}"):
                wrong.append(f"{pkg}.{field}: {hint.__module__}.{hint.__name__}")
    assert wrong == []


def test_a_part_imports_only_public_modules_of_packages() -> None:
    private = []
    for pkg in _parts.part_names():
        tree = ast.parse((APP_DIR / f"fields_{pkg}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level and pkg != "app":
                private += [f"{pkg}: {node.module}" for part in (node.module or "").split(".") if part.startswith("_")]
    assert private == []


@pytest.mark.parametrize("pkg", [p for p in _parts.part_names() if p not in NOT_FEATURES])
def test_a_feature_part_that_is_done_names_its_step(pkg: str) -> None:
    module = _parts.part(pkg)
    fields = typing.get_type_hints(module.Fields)
    assert (module.STEP is not None) == bool(fields or module.NOT_A_FIELD), f"{pkg}: STEP and the fields must go together"
