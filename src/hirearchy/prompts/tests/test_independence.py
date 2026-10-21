"""``prompts`` sits above the kernel and the features it reads: its code imports nothing else of ``hirearchy``, and of those only what is public.

import-linter checks the layers over the whole graph; this is the package's own guard (ARCHITECTURE.md 2.2 and 4, allowed dependencies). The fakes
(``testing.py``) and the tests obey the same rule, through the ``testing`` modules of those packages."""

from __future__ import annotations

import ast
from pathlib import Path

HIREARCHY = Path(__file__).resolve().parents[2]
OWN = "hirearchy.prompts"
ALLOWED = (
    OWN, "hirearchy.kernel", "hirearchy.agents", "hirearchy.settings", "hirearchy.access", "hirearchy.mail", "hirearchy.strays", "hirearchy.budget", "hirearchy.eligibility",
    "hirearchy.services", "hirearchy.reflection",
)


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
    """The modules of ``hirearchy`` that are neither the package's own nor one it may depend on."""
    return [m for m in modules if (m == "hirearchy" or m.startswith("hirearchy.")) and not any(m == p or m.startswith(p + ".") for p in ALLOWED)]


def private_of_others(modules: list[str]) -> list[str]:
    """Imports of a ``_`` module of another package."""
    return [m for m in modules if not m.startswith(OWN) and any(part.startswith("_") for part in m.split(".")[2:])]


def scan() -> dict[Path, list[str]]:
    found: dict[Path, list[str]] = {}
    for path in sorted((HIREARCHY / "prompts").rglob("*.py")):
        relative = path.relative_to(HIREARCHY / "prompts")
        found[path] = imports_of(path.read_text(encoding="utf-8"), ["hirearchy", "prompts", *relative.parts[:-1]])
    return found


def test_the_package_imports_only_itself_and_the_packages_it_may_depend_on() -> None:
    offenders = {str(p.relative_to(HIREARCHY)): bad for p, mods in scan().items() if (bad := foreign(mods))}
    assert not offenders, f"prompts may import only the kernel, agents, settings, access, mail, strays, budget, eligibility, services and reflection: {offenders}"


def test_no_private_module_of_another_package_is_imported() -> None:
    offenders = {str(p.relative_to(HIREARCHY)): bad for p, mods in scan().items() if (bad := private_of_others(mods))}
    assert not offenders, f"prompts imports private modules of other packages: {offenders}"


def test_the_scan_sees_the_package() -> None:
    assert len(scan()) >= 6
