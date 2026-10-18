"""``settings`` and ``locator`` sit just above the kernel: their code imports nothing else of ``orgmcp``.

import-linter checks the layers over the whole graph; this is the packages' own guard (ARCHITECTURE.md 2.2, allowed dependencies)."""

from __future__ import annotations

import ast
from pathlib import Path

ORGMCP = Path(__file__).resolve().parents[2]
PACKAGES = ("settings", "locator")


def imports_of(source: str, package: list[str]) -> list[str]:
    """Every module ``source`` imports, as absolute dotted names; ``package`` is the dotted package of the file."""
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


def foreign(modules: list[str], own: str) -> list[str]:
    """The modules that are neither the package's own, nor the kernel's, nor outside ``orgmcp``."""
    ok = (own, "orgmcp.kernel")
    return [m for m in modules if (m == "orgmcp" or m.startswith("orgmcp.")) and not any(m == p or m.startswith(p + ".") for p in ok)]


def test_the_packages_import_only_themselves_and_the_kernel() -> None:
    offenders: dict[str, list[str]] = {}
    for name in PACKAGES:
        for path in sorted((ORGMCP / name).rglob("*.py")):
            relative = path.relative_to(ORGMCP / name)
            if "tests" in relative.parts:
                continue
            package = ["orgmcp", name, *relative.parts[:-1]]
            bad = foreign(imports_of(path.read_text(encoding="utf-8"), package), f"orgmcp.{name}")
            if bad:
                offenders[f"{name}/{relative}"] = bad
    assert not offenders, f"settings and locator may import only the kernel: {offenders}"
