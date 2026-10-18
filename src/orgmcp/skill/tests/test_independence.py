"""``skill`` sits just above the kernel: its code imports nothing else of ``orgmcp`` (ARCHITECTURE.md 2.2, allowed dependencies).

import-linter checks the layers over the whole graph; this is the package's own guard, ``_legacy.py`` included."""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]


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


def test_the_package_imports_only_itself_and_the_kernel() -> None:
    offenders: dict[str, list[str]] = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = path.relative_to(PACKAGE)
        if "tests" in relative.parts:
            continue
        package = ["orgmcp", "skill", *relative.parts[:-1]]
        bad = [m for m in imports_of(path.read_text(encoding="utf-8"), package)
               if (m == "orgmcp" or m.startswith("orgmcp.")) and not any(m == p or m.startswith(p + ".") for p in ("orgmcp.skill", "orgmcp.kernel"))]
        if bad:
            offenders[str(relative)] = bad
    assert not offenders, f"skill may import only the kernel: {offenders}"
