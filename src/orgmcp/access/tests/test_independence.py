"""``access`` sits above the kernel, ``agents`` and ``settings``: its code imports nothing else of ``orgmcp``.

import-linter checks the layers over the whole graph; this is the package's own guard (ARCHITECTURE.md 2.2, allowed dependencies).
The in-memory fake and the tests are not production code, but they obey the same rule (through the ``testing`` modules of the packages)."""

from __future__ import annotations

import ast
from pathlib import Path

ORGMCP = Path(__file__).resolve().parents[2]
OWN = "orgmcp.access"
ALLOWED = (OWN, "orgmcp.kernel", "orgmcp.agents", "orgmcp.settings")


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
    """The modules of ``orgmcp`` that are neither the package's own nor one it may depend on."""
    return [m for m in modules if (m == "orgmcp" or m.startswith("orgmcp.")) and not any(m == p or m.startswith(p + ".") for p in ALLOWED)]


def private_of_others(modules: list[str]) -> list[str]:
    """Imports of a ``_`` module of another package."""
    return [m for m in modules if not m.startswith(OWN) and any(part.startswith("_") for part in m.split(".")[2:])]


def scan() -> dict[Path, list[str]]:
    found: dict[Path, list[str]] = {}
    for path in sorted((ORGMCP / "access").rglob("*.py")):
        relative = path.relative_to(ORGMCP / "access")
        found[relative] = imports_of(path.read_text(encoding="utf-8"), ["orgmcp", "access", *relative.parts[:-1]])
    return found


def test_the_package_imports_only_itself_the_kernel_agents_and_settings() -> None:
    offenders = {str(path): bad for path, modules in scan().items() if (bad := foreign(modules))}
    assert not offenders, f"access may import only the kernel, agents and settings: {offenders}"


def test_no_module_imports_a_private_module_of_another_package() -> None:
    offenders = {str(path): bad for path, modules in scan().items() if (bad := private_of_others(modules))}
    assert not offenders, f"only the composition root may import the private modules of a package: {offenders}"
