"""``telemetry`` imports only the kernel, ``eventlog``, ``settings`` and ``snapshots`` (ARCHITECTURE.md 2.2), through their ``api``.

import-linter checks the layers over the whole graph; this is the package's own guard. The legacy module ``_legacy`` is held to it too: it
reaches the process defaults through a hook that ``orgmcp.app`` installs, never by importing the composition root."""

from __future__ import annotations

import ast
from pathlib import Path

ORGMCP = Path(__file__).resolve().parents[2]
ALLOWED = ("orgmcp.telemetry", "orgmcp.kernel", "orgmcp.eventlog", "orgmcp.settings", "orgmcp.snapshots")


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
    return [m for m in modules if (m == "orgmcp" or m.startswith("orgmcp.")) and not any(m == p or m.startswith(p + ".") for p in ALLOWED)]


def test_the_package_imports_only_what_it_may() -> None:
    offenders: dict[str, list[str]] = {}
    for path in sorted((ORGMCP / "telemetry").rglob("*.py")):
        relative = path.relative_to(ORGMCP / "telemetry")
        if "tests" in relative.parts:
            continue
        bad = foreign(imports_of(path.read_text(encoding="utf-8"), ["orgmcp", "telemetry", *relative.parts[:-1]]))
        if bad:
            offenders[str(relative)] = bad
    assert not offenders, f"telemetry may import only {ALLOWED}: {offenders}"


def test_the_package_never_imports_the_private_modules_of_another_package() -> None:
    offenders: dict[str, list[str]] = {}
    for path in sorted((ORGMCP / "telemetry").rglob("*.py")):
        relative = path.relative_to(ORGMCP / "telemetry")
        if "tests" in relative.parts:
            continue
        mods = imports_of(path.read_text(encoding="utf-8"), ["orgmcp", "telemetry", *relative.parts[:-1]])
        bad = [m for m in mods if m.startswith("orgmcp.") and not m.startswith("orgmcp.telemetry") and any(p.startswith("_") for p in m.split("."))]
        if bad:
            offenders[str(relative)] = bad
    assert not offenders, offenders
