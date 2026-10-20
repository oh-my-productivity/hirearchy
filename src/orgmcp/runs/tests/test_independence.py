"""``runs`` sits just above the kernel: its code imports nothing else of ``orgmcp``.

import-linter checks the layers over the whole graph; this is the package's own guard (ARCHITECTURE.md 2.2, allowed dependencies)."""

from __future__ import annotations

import ast
from pathlib import Path

ORGMCP = Path(__file__).resolve().parents[2]
PACKAGE = "runs"


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


def foreign(modules: list[str]) -> list[str]:
    """The modules that are neither the package's own, nor the kernel's, nor outside ``orgmcp``."""
    ok = (f"orgmcp.{PACKAGE}", "orgmcp.kernel")
    return [m for m in modules if (m == "orgmcp" or m.startswith("orgmcp.")) and not any(m == p or m.startswith(p + ".") for p in ok)]


def test_the_package_imports_only_itself_and_the_kernel() -> None:
    offenders: dict[str, list[str]] = {}
    for path in sorted((ORGMCP / PACKAGE).rglob("*.py")):
        relative = path.relative_to(ORGMCP / PACKAGE)
        if "tests" in relative.parts:
            continue
        package = ["orgmcp", PACKAGE, *relative.parts[:-1]]
        bad = foreign(imports_of(path.read_text(encoding="utf-8"), package))
        if bad:
            offenders[str(relative)] = bad
    assert not offenders, f"runs may import only the kernel: {offenders}"
