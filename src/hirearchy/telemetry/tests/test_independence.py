"""``telemetry`` imports only the kernel, ``eventlog``, ``settings`` and ``snapshots`` (ARCHITECTURE.md 2.2), through their ``api``.

import-linter checks the layers over the whole graph; this is the package's own guard."""

from __future__ import annotations

import ast
from pathlib import Path

HIREARCHY = Path(__file__).resolve().parents[2]
ALLOWED = ("hirearchy.telemetry", "hirearchy.kernel", "hirearchy.eventlog", "hirearchy.settings", "hirearchy.snapshots")


def imports_of(source: str, package: list[str]) -> list[str]:
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = package[: len(package) - (node.level - 1)] if node.level else []
            module = ".".join([*base, *([node.module] if node.module else [])])
            found.append(module)
            found += [f"{module}.{alias.name}" for alias in node.names]
    return found


def foreign(modules: list[str]) -> list[str]:
    return [m for m in modules if (m == "hirearchy" or m.startswith("hirearchy.")) and not any(m == p or m.startswith(p + ".") for p in ALLOWED)]


def test_the_package_imports_only_what_it_may() -> None:
    offenders: dict[str, list[str]] = {}
    for path in sorted((HIREARCHY / "telemetry").rglob("*.py")):
        relative = path.relative_to(HIREARCHY / "telemetry")
        if "tests" in relative.parts:
            continue
        bad = foreign(imports_of(path.read_text(encoding="utf-8"), ["hirearchy", "telemetry", *relative.parts[:-1]]))
        if bad:
            offenders[str(relative)] = bad
    assert not offenders, f"telemetry may import only {ALLOWED}: {offenders}"


def test_the_package_never_imports_the_private_modules_of_another_package() -> None:
    offenders: dict[str, list[str]] = {}
    for path in sorted((HIREARCHY / "telemetry").rglob("*.py")):
        relative = path.relative_to(HIREARCHY / "telemetry")
        if "tests" in relative.parts:
            continue
        mods = imports_of(path.read_text(encoding="utf-8"), ["hirearchy", "telemetry", *relative.parts[:-1]])
        bad = [m for m in mods if m.startswith("hirearchy.") and not m.startswith("hirearchy.telemetry") and any(p.startswith("_") for p in m.split("."))]
        if bad:
            offenders[str(relative)] = bad
    assert not offenders, offenders
