"""The legacy-exports ledger (ARCHITECTURE.md 6.5).

During the strangler phase each legacy module is converted in place to a package that exports its ``api`` plus the old names
(``LEGACY_EXPORTS``); until a module is converted, its old public names are simply the names it defines. This ledger lists, per
legacy module, every public name that may still be exported and the step that removes it. It only shrinks:

* a public name that the module defines or exports and that is NOT listed fails ``check`` (nobody adds a legacy export);
* a listed name that the module no longer defines fails ``check`` too (delete the entry in the step that removed it: the ledger
  and the code move together). A step that converts a module deletes the entries it removes, in its own table (disjoint hunks).

Removal step ``"E3"`` = the final step that deletes the legacy layer; ``"permanent"`` = the compatibility surface that stays
(manager decision 10.3): ``orgmcp.core`` (all of its names: README documents ``DEFAULT_MODEL`` and ``Org``), ``orgmcp.progress.progress``,
the console script / ``python -m orgmcp`` (``orgmcp.main``, which is imported, not defined, in ``orgmcp/__init__.py``).
"""

from __future__ import annotations

import ast
from pathlib import Path

from . import legacy_symbols
from .paths import SRC


def _e3(names: str) -> dict[str, str]:
    return {name: "E3" for name in names.split()}


PERMANENT_MODULES = {"core"}  # every name of these modules stays: the ledger holds the wildcard "*"

LEGACY_EXPORTS: dict[str, dict[str, str]] = {
    "core": {"*": "permanent"},
    "scheduler": _e3("file_confinement"),
    "progress": {"progress": "permanent"},  # orgmcp.progress.progress(org, task_id=None) is documented in the README
}


def public_names(path: Path) -> list[str]:
    """Public names a legacy module defines at module level (functions, classes, constants), in file order."""
    names: list[str] = []
    for stmt in legacy_symbols._toplevel(ast.parse(path.read_text(encoding="utf-8")).body):
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(stmt.name)
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            names.extend(sub.id for target in targets for sub in ast.walk(target) if isinstance(sub, ast.Name))
    return [n for n in dict.fromkeys(names) if not n.startswith("_")]


def _bound_names(path: Path) -> set[str]:
    """Names bound at module level of an ``__init__.py`` (imports, definitions, assignments)."""
    bound: set[str] = set()
    for stmt in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(stmt, ast.ImportFrom):
            bound.update((a.asname or a.name) for a in stmt.names)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(stmt.name)
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            bound.update(sub.id for target in targets for sub in ast.walk(target) if isinstance(sub, ast.Name))
    return bound


def check(src: Path = SRC) -> list[str]:
    """Problems between the ledger and the code under ``src`` (empty when they agree)."""
    problems = []
    for module, entries in LEGACY_EXPORTS.items():
        flat, package = src / f"{module}.py", src / module / "__init__.py"
        if "*" in entries:
            continue
        if flat.is_file():
            defined = public_names(flat)
            problems += [f"{module}.{n} is public but not in the legacy-exports ledger (tests/architecture/legacy_exports.py): "
                         "a legacy module may not gain exports" for n in defined if n not in entries]
            problems += [f"{module}.{n} is in the ledger but the module no longer defines it: delete the entry"
                         for n in entries if n not in defined]
        elif package.is_file():
            bound = _bound_names(package)
            problems += [f"{module}.{n} is in the ledger but the package no longer exports it: delete the entry"
                         for n in entries if n not in bound]
        else:
            problems.append(f"{module}: the legacy module no longer exists: delete its table in the ledger")
    return problems


def exported_names_by_package(src: Path | None = None) -> dict[str, set[str]]:
    """{package: legacy names it may still export besides its api}: the ledger tables of the modules that became packages."""
    root = src or SRC
    return {module: set(entries) for module, entries in LEGACY_EXPORTS.items()
            if "*" not in entries and (root / module / "__init__.py").is_file()}
