"""Which symbols of ARCHITECTURE.md section 5 have reached their target package? (the done-check of every feature step)

    uv run python -m tests.architecture.mapping_status mail          # the slice of one package
    uv run python -m tests.architecture.mapping_status all           # a count per package
    uv run python -m tests.architecture.mapping_status mail --moved  # also list what has moved

Every row of the mapping tables names a legacy symbol and its target. A row belongs to the package of its FIRST target (the
first backticked token that starts with a package of the map: ``mail.MailboxReader``, ``mail/_mailbox.py::FsMailbox._wakes``, or just
``kernel`` for "moves to the kernel under its own name"). It is **moved** when that target exists in ``src/orgmcp/<package>/``:
the class, function or constant (any module of the package), the file for a ``pkg/_file.py`` target, the method for a
``Class.method`` target. Rows whose target is "deleted: ..." (nothing to move) and rows without a recognisable target are skipped.

Exit status: 0 when no symbol of the slice is unmoved, 1 otherwise, 2 for an unknown package.
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import document, graph
from .checks import Tree
from .paths import DOCUMENT, SRC

_TARGET = re.compile(r"^(?P<package>[a-z_]+)(?:(?P<sep>[./])(?P<rest>.*))?$")


@dataclass
class Row:
    section: str
    symbol: str
    target: str  # the first target token, e.g. "mail.MailboxReader"
    package: str
    reason: str = ""


@dataclass
class Result:
    package: str = ""
    moved: list[Row] = field(default_factory=list)
    unmoved: list[Row] = field(default_factory=list)


def primary_target(cell: str) -> tuple[str, str] | None:
    """(package, token) of the first backticked token of a target cell that points into a package of the map, else None."""
    if re.match(r"^\W*deleted\b", cell):
        return None
    for segment in re.findall(r"`([^`]+)`", cell):
        token = re.sub(r"\(.*$", "", segment.split()[0]) if segment.split() else ""
        match = _TARGET.match(token)
        if match and match.group("package") in graph.ALL_PACKAGES:
            return match.group("package"), token
    return None


def _defined(directory: Path) -> tuple[dict[str, dict[str, set[str]]], set[str]]:
    """({file stem: {top-level name: member names}}, every name defined anywhere in the package)."""
    files: dict[str, dict[str, set[str]]] = {}
    everywhere: set[str] = set()
    if not directory.is_dir():
        return files, everywhere
    for path in sorted(directory.rglob("*.py")):
        if "tests" in path.relative_to(directory).parts:
            continue
        names: dict[str, set[str]] = {}
        for stmt in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names[stmt.name] = set()
            elif isinstance(stmt, ast.ClassDef):
                names[stmt.name] = {m.name for m in stmt.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
            elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
                for target in targets:
                    names.update({sub.id: set() for sub in ast.walk(target) if isinstance(sub, ast.Name)})
        files[path.stem] = names
        everywhere |= set(names)
    return files, everywhere


def _is_moved(row: Row, tree: Tree) -> tuple[bool, str]:
    files, everywhere = _defined(tree.directory / row.package)
    if not files:
        return False, f"package {row.package} does not exist yet"
    match = _TARGET.match(row.target)
    rest = (match.group("rest") if match else "") or ""
    if match and match.group("sep") == "/":  # pkg/_file.py::Class.member
        file_part, _, symbol = rest.partition("::")
        stem = Path(file_part).stem
        if stem not in files:
            return False, f"{row.package}/{file_part} does not exist"
        parts = symbol.split(".") if symbol else []
        if parts and parts[0] not in files[stem]:
            return False, f"{parts[0]} is not defined in {row.package}/{file_part}"
        if len(parts) > 1 and parts[1] not in files[stem][parts[0]]:
            return False, f"{parts[0]}.{parts[1]} is not defined in {row.package}/{file_part}"
        return True, ""
    parts = rest.split(".") if rest else [row.symbol]  # "pkg.Name.member" or "pkg" alone: the symbol keeps its name
    if parts[0] not in everywhere:
        return False, f"{parts[0]} is not defined in {row.package}"
    if len(parts) > 1:
        members = [names[parts[0]] for names in files.values() if parts[0] in names]
        if not any(parts[1] in m for m in members):
            return False, f"{parts[0]}.{parts[1]} is not defined in {row.package}"
    return True, ""


def status(package: str, markdown: str, tree: Tree) -> Result:
    """The moved and unmoved symbols of the slice of ``package`` (rows are in document order)."""
    result = Result(package)
    for mapping in document.mapping_rows(markdown):
        target = primary_target(mapping.target)
        if target is None or target[0] != package:
            continue
        row = Row(mapping.section, mapping.symbol, target[1], package)
        moved, row.reason = _is_moved(row, tree)
        (result.moved if moved else result.unmoved).append(row)
    return result


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    show_moved = "--moved" in argv
    if len(args) != 1 or (args[0] != "all" and args[0] not in graph.ALL_PACKAGES):
        print(__doc__)
        print("packages:", ", ".join(graph.ALL_PACKAGES))
        return 2
    markdown, tree = DOCUMENT.read_text(encoding="utf-8"), Tree(SRC)
    if args[0] == "all":
        total = 0
        for name in graph.ALL_PACKAGES:
            result = status(name, markdown, tree)
            total += len(result.unmoved)
            print(f"{name:14} moved {len(result.moved):4}  unmoved {len(result.unmoved):4}")
        return int(total > 0)
    result = status(args[0], markdown, tree)
    print(f"{args[0]}: {len(result.moved)} moved, {len(result.unmoved)} unmoved")
    for row in result.unmoved:
        print(f"  unmoved  {row.section} {row.symbol} -> {row.target}  ({row.reason})")
    if show_moved:
        for row in result.moved:
            print(f"  moved    {row.section} {row.symbol} -> {row.target}")
    return int(bool(result.unmoved))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
