"""The symbols of the legacy modules, for the mapping check (``test_mapping_complete``).

Every module-level function and class of a legacy module, and every method of ``Org``, ``Message``, ``Scheduler``, ``DashData`` and
``LenientOrg`` (the classes that are split), must appear in the mapping table of ARCHITECTURE.md section 5
(``document.mapping_symbols``). Constants are listed "where they matter" (section 5 intro) and the methods of data classes move with
their class: neither is required. Dunder names are mechanical and not listed.
A legacy module that was converted in place is read from ``<module>/_legacy.py`` (what is left to move); once it is gone, nothing
is left to check.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from . import document

# legacy module -> the sections of ARCHITECTURE.md section 5 that map its symbols (a section may cover several modules)
SECTIONS: dict[str, tuple[str, ...]] = {
    "core": ("5.1", "5.2", "5.3"),
    "scheduler": ("5.4", "5.5"),
    "server": ("5.6",),
    "cli": ("5.7",),
    "cli_obs": ("5.7",),
    "__init__": ("5.7",),
    "__main__": ("5.7",),
    "services": ("5.8",),
    "telemetry": ("5.9",),
    "observe": ("5.10",),
    "progress": ("5.11",),
    "health": ("5.11",),
    "review": ("5.11",),
    "blueprint": ("5.12",),
    "blueprint_examples": ("5.12",),
    "templates": ("5.13",),
    "upgrade": ("5.13",),
    "skill": ("5.13",),
    "dashboard_events": ("5.14",),
    "dashboard_data": ("5.14",),
    "dashboard": ("5.14",),
}


def module_file(src: Path, module: str) -> Path | None:
    """The file that holds the legacy code of ``module``: ``<module>.py``, or ``<module>/_legacy.py`` after an in-place conversion."""
    for candidate in (src / f"{module}.py", src / module / "_legacy.py"):
        if candidate.is_file():
            return candidate
    return None


SPLIT_CLASSES = frozenset({"Org", "Message", "Scheduler", "DashData", "LenientOrg"})


def _toplevel(body: list[ast.stmt]) -> Iterator[ast.stmt]:
    for stmt in body:
        yield stmt
        if isinstance(stmt, (ast.If, ast.Try)):
            yield from _toplevel([*stmt.body, *stmt.orelse, *getattr(stmt, "finalbody", []),
                                  *(s for h in getattr(stmt, "handlers", []) for s in h.body)])


def _dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def symbols(path: Path) -> list[str]:
    """Qualified symbols of one legacy module, in file order: ``name`` and ``Class.method``."""
    out: list[str] = []
    for stmt in _toplevel(ast.parse(path.read_text(encoding="utf-8")).body):
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(stmt.name)
        elif isinstance(stmt, ast.ClassDef):
            out.append(stmt.name)
            if stmt.name in SPLIT_CLASSES:
                out.extend(f"{stmt.name}.{m.name}" for m in stmt.body
                           if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and not _dunder(m.name))
    return [s for s in dict.fromkeys(out) if not _dunder(s.split(".")[0])]


def missing_from_mapping(src: Path, markdown: str) -> list[str]:
    """``module.symbol`` for every symbol of the legacy modules under ``src`` that section 5 does not mention."""
    documented = document.mapping_symbols(markdown)
    missing = []
    for module, sections in SECTIONS.items():
        path = module_file(src, module)
        if path is None:
            continue
        known = set().union(*(documented.get(s, set()) for s in sections))
        missing.extend(f"{module}.{s}" for s in symbols(path) if s.split(".")[-1] not in known)
    return missing
