"""``bootstrap`` depends on the kernel, ``settings``, ``snapshots`` and ``templates`` only, and on their public modules (ARCHITECTURE.md 2.2, 4.3).

import-linter checks the layers over the whole graph; this is the package's own guard, ``testing.py`` included."""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
ALLOWED = ("hirearchy.bootstrap", "hirearchy.kernel", "hirearchy.settings", "hirearchy.snapshots", "hirearchy.templates")


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


def private(module: str) -> bool:
    return any(part.startswith("_") for part in module.split(".")[2:])


def test_the_package_imports_only_the_packages_it_may_depend_on() -> None:
    offenders: dict[str, list[str]] = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = path.relative_to(PACKAGE)
        if "tests" in relative.parts:
            continue
        package = ["hirearchy", "bootstrap", *relative.parts[:-1]]
        bad = [m for m in imports_of(path.read_text(encoding="utf-8"), package) if m.startswith("hirearchy.")
               and not any(m == p or m.startswith(p + ".") for p in ALLOWED)]
        if bad:
            offenders[str(relative)] = bad
    assert not offenders, f"bootstrap may import only {ALLOWED}: {offenders}"


def test_it_never_reaches_into_a_private_module_of_another_package() -> None:
    offenders: dict[str, list[str]] = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = path.relative_to(PACKAGE)
        if "tests" in relative.parts:
            continue
        package = ["hirearchy", "bootstrap", *relative.parts[:-1]]
        bad = [m for m in imports_of(path.read_text(encoding="utf-8"), package)
               if m.startswith("hirearchy.") and not m.startswith("hirearchy.bootstrap") and private(m)]
        if bad:
            offenders[str(relative)] = bad
    assert not offenders, offenders
