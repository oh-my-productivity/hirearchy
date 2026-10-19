"""``reflection`` sits above ``agents``, ``runs``, ``settings``, ``mail`` and ``services``: its code imports nothing else of ``orgmcp`` but the kernel
and their public modules (ARCHITECTURE.md 2.2 and 4, allowed dependencies).

import-linter checks the layers over the whole graph; this is the package's own guard. The fakes and the harness (``testing.py``) and the tests obey
the same rule, through the ``testing`` modules of those packages (and the ones those harnesses are built on, ``dispatch``'s world through
``services``'); the legacy modules and the facade are reached by name."""

from __future__ import annotations

import ast
from pathlib import Path

ORGMCP = Path(__file__).resolve().parents[2]
OWN = "orgmcp.reflection"
PUBLIC_OF = ("agents", "runs", "settings", "mail", "services")


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
    """The modules that are neither the package's own, nor the kernel's, nor public in the packages below it (their api and their fakes)."""

    def allowed(module: str) -> bool:
        if module == OWN or module.startswith(OWN + ".") or module == "orgmcp.kernel" or module.startswith("orgmcp.kernel."):
            return True
        parts = module.split(".")
        return parts[:2] in [["orgmcp", name] for name in PUBLIC_OF] and not any(part.startswith("_") for part in parts[2:])

    return [m for m in modules if (m == "orgmcp" or m.startswith("orgmcp.")) and m != "orgmcp" and not allowed(m)]


def test_the_package_imports_only_itself_the_kernel_and_the_apis_of_the_packages_below() -> None:
    offenders: dict[str, list[str]] = {}
    for path in sorted((ORGMCP / "reflection").rglob("*.py")):
        relative = path.relative_to(ORGMCP / "reflection")
        package = ["orgmcp", "reflection", *relative.parts[:-1]]
        bad = foreign(imports_of(path.read_text(encoding="utf-8"), package))
        if bad:
            offenders[str(relative)] = bad
    assert not offenders, f"reflection may import only the kernel and the api (and fakes) of {PUBLIC_OF}: {offenders}"
