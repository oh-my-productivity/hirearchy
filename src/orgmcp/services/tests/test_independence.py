"""``services`` sits above ``agents``, ``settings``, ``mail``, ``delivery`` and ``dispatch``: its code imports nothing else of ``orgmcp`` but the
kernel and their apis.

import-linter checks the layers over the whole graph; this is the package's own guard (ARCHITECTURE.md 2.2, allowed dependencies). It also holds for
the harness in ``testing.py`` (which uses the fakes and harnesses of those packages) and for the tests, which may also import the contract suite of
``dispatch`` for the port ``ReworkContext`` that this package implements."""

from __future__ import annotations

import ast
from pathlib import Path

ORGMCP = Path(__file__).resolve().parents[2]
OWN = "orgmcp.services"
PUBLIC_OF = ("agents", "settings", "mail", "delivery", "dispatch", "templates", "access", "budget")  # the last three: only through dispatch's harness
CONTRACT_SUITE = "orgmcp.dispatch.tests.test_contract_rework_context"


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
        if module == CONTRACT_SUITE or module.startswith(CONTRACT_SUITE + "."):
            return True
        parts = module.split(".")
        return parts[:2] in [["orgmcp", name] for name in PUBLIC_OF] and not any(part.startswith("_") for part in parts[2:])

    return [m for m in modules if (m == "orgmcp" or m.startswith("orgmcp.")) and m != "orgmcp" and not allowed(m)]


def test_the_package_imports_only_itself_the_kernel_and_the_apis_of_the_packages_below() -> None:
    offenders: dict[str, list[str]] = {}
    for path in sorted((ORGMCP / "services").rglob("*.py")):
        relative = path.relative_to(ORGMCP / "services")
        package = ["orgmcp", "services", *relative.parts[:-1]]
        bad = foreign(imports_of(path.read_text(encoding="utf-8"), package))
        if bad:
            offenders[str(relative)] = bad
    assert not offenders, f"services may import only the kernel and the api (and fakes) of agents, settings, mail, delivery and dispatch: {offenders}"


def test_the_code_of_the_package_does_not_use_the_templates_the_access_or_the_budget_directly() -> None:
    offenders = []
    for path in sorted((ORGMCP / "services").glob("*.py")):
        if path.name == "testing.py":
            continue
        package = ["orgmcp", "services"]
        offenders += [(path.name, m) for m in imports_of(path.read_text(encoding="utf-8"), package) if m.split(".")[:2] in (["orgmcp", "templates"], ["orgmcp", "access"], ["orgmcp", "budget"])]
    assert not offenders, offenders
