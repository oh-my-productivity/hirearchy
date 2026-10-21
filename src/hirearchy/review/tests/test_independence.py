"""``review`` sits above ``agents``, ``runs``, ``settings``, ``templates``, ``mail``, ``delivery``, ``budget``, ``eligibility`` and ``health``: its code
imports nothing else of ``hirearchy`` but the kernel and their public modules (ARCHITECTURE.md 2.2 and 4, allowed dependencies).

import-linter checks the layers over the whole graph; this is the package's own guard. The fakes and the harness (``testing.py``) and the tests obey the
same rule, through the ``testing`` modules of those packages; the facade is reached by name."""

from __future__ import annotations

import ast
from pathlib import Path

HIREARCHY = Path(__file__).resolve().parents[2]
OWN = "hirearchy.review"
PUBLIC_OF = ("agents", "runs", "settings", "templates", "mail", "delivery", "budget", "eligibility", "health")


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
        if module == OWN or module.startswith(OWN + ".") or module == "hirearchy.kernel" or module.startswith("hirearchy.kernel."):
            return True
        parts = module.split(".")
        return parts[:2] in [["hirearchy", name] for name in PUBLIC_OF] and not any(part.startswith("_") for part in parts[2:])

    return [m for m in modules if (m == "hirearchy" or m.startswith("hirearchy.")) and m != "hirearchy" and not allowed(m)]


def test_the_package_imports_only_itself_the_kernel_and_the_apis_of_the_packages_below() -> None:
    offenders: dict[str, list[str]] = {}
    for path in sorted((HIREARCHY / "review").rglob("*.py")):
        relative = path.relative_to(HIREARCHY / "review")
        package = ["hirearchy", "review", *relative.parts[:-1]]
        bad = foreign(imports_of(path.read_text(encoding="utf-8"), package))
        if bad:
            offenders[str(relative)] = bad
    assert not offenders, f"review may import only the kernel and the api (and fakes) of {PUBLIC_OF}: {offenders}"
