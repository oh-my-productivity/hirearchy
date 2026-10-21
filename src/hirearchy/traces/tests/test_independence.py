"""``traces`` sits just above ``mail``: its code imports nothing else of ``hirearchy`` but the kernel and ``mail`` (through its api).

import-linter checks the layers over the whole graph; this is the package's own guard (ARCHITECTURE.md 2.2, allowed dependencies). It also
holds for the harness in ``testing.py`` (which uses the in-memory mailboxes of ``mail``) and for the tests."""

from __future__ import annotations

import ast
from pathlib import Path

HIREARCHY = Path(__file__).resolve().parents[2]
OWN = "hirearchy.traces"


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
    """The modules that are neither the package's own, nor the kernel's, nor public in ``mail`` (its api and its fakes)."""

    def allowed(module: str) -> bool:
        if module == OWN or module.startswith(OWN + ".") or module == "hirearchy.kernel" or module.startswith("hirearchy.kernel."):
            return True
        parts = module.split(".")
        return parts[:2] == ["hirearchy", "mail"] and not any(part.startswith("_") for part in parts[2:])  # not a private module of mail

    return [m for m in modules if (m == "hirearchy" or m.startswith("hirearchy.")) and m != "hirearchy" and not allowed(m)]


def test_the_package_imports_only_itself_the_kernel_and_the_mail_api() -> None:
    offenders: dict[str, list[str]] = {}
    for path in sorted((HIREARCHY / "traces").rglob("*.py")):
        relative = path.relative_to(HIREARCHY / "traces")
        package = ["hirearchy", "traces", *relative.parts[:-1]]
        bad = foreign(imports_of(path.read_text(encoding="utf-8"), package))
        if bad:
            offenders[str(relative)] = bad
    assert not offenders, f"traces may import only the kernel and the api of mail: {offenders}"
