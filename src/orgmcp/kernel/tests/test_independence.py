"""The kernel is the bottom layer: nothing in ``orgmcp/kernel`` (its tests included) imports anything else of ``orgmcp``.

import-linter checks the same rule over the whole import graph; this test is the kernel's own guard, so a step
that touches only the kernel notices a violation without the global tooling."""

from __future__ import annotations

import ast
from pathlib import Path

KERNEL = Path(__file__).resolve().parent.parent


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


def outside_the_kernel(modules: list[str]) -> list[str]:
    return [m for m in modules if m == "orgmcp" or (m.startswith("orgmcp.") and not (m == "orgmcp.kernel" or m.startswith("orgmcp.kernel.")))]


def test_the_kernel_imports_only_itself_and_the_library() -> None:
    offenders = {}
    for path in sorted(KERNEL.rglob("*.py")):
        package = ["orgmcp", "kernel", *path.relative_to(KERNEL).parts[:-1]]
        bad = outside_the_kernel(imports_of(path.read_text(encoding="utf-8"), package))
        if bad:
            offenders[str(path.relative_to(KERNEL))] = bad
    assert not offenders, f"the kernel must not import the rest of orgmcp: {offenders}"


def test_the_guard_sees_a_violation() -> None:
    source = "from orgmcp.core import Org\nfrom .. import api\nfrom ... import health\nimport orgmcp.scheduler\nfrom orgmcp import cli\n"
    found = outside_the_kernel(imports_of(source, ["orgmcp", "kernel", "tests"]))
    assert found == ["orgmcp.core", "orgmcp.core.Org", "orgmcp", "orgmcp.health", "orgmcp.scheduler", "orgmcp", "orgmcp.cli"]
