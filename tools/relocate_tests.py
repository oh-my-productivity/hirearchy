#!/usr/bin/env python3
"""Moves the tests of ``tests/test_*.py`` to their destinations, as ``tests/architecture/relocation.yaml`` says (ARCHITECTURE.md 7.3, step E0).

    uv run python tools/relocate_tests.py plan                   # dry run: counts per group and per destination; errors make it exit 1
    uv run python tools/relocate_tests.py apply --group a        # move the tests of group a: write the destinations, prune the sources
    uv run python tools/relocate_tests.py prune --group a        # only the source side of ``apply`` (nothing is written to a destination)

The manifest names, for every destination file, the tests that move there (``Class::name`` for a method of a test class) and how many
tests pytest collects for each. A destination belongs to exactly one group (the E1 step that moves it), by the package it lives in.

What a move is:

* a pure move: the text of every moved statement is copied verbatim (decorators, marks, comments directly above, source order). The
  only rewrite is ``Path(__file__)...`` expressions, which become the constants of ``tests/testkit`` (``testkit.FAKE_AGENT``,
  ``testkit.REPO / "examples"``, ...), because the file is no longer where they point from. Any other use of ``__file__`` is an error;
* a test takes with it the module-level helpers, constants, fixtures (found by parameter name, ``usefixtures`` and ``name=``) and the
  autouse fixtures of its module; each destination gets its own copy, and imports are written only for the names the destination uses;
* an existing destination is extended, never overwritten; a test or helper of the same name that differs there is an error, and so is a name
  that would mean something else in the merged module (a fixture of the destination that the moved tests get from conftest, an autouse fixture,
  a module-level pytestmark, a helper that two sources of one destination define differently): the manifest then names another file;
* an import the import contracts forbid in the package of the destination (facade, server, scheduler, yaml ...) is written as
  ``testkit.legacy.<module>`` (tests/testkit/legacy: the same module object, invisible to import-linter);
* a new file under src/orgmcp starts with ``# mypy: ignore-errors`` (moved tests are untyped), a new test directory gets an ``__init__.py``;
* the source loses the moved tests and then everything nothing needs any more (helpers, fixtures, imports); a source without tests is deleted.

``apply`` and ``prune`` are deterministic and idempotent, and the result does not depend on the order in which the groups are run: what a source
keeps is a function of the tests that are left in it (everything reachable from them), and a destination depends only on its own tests.
That is what lets the manager resolve a merge conflict in a shared source by taking the integration version and running ``prune --group X``.

Nothing is written unless the whole run is free of errors. Exit status: 0 ok, 1 errors in the manifest or the sources, 2 usage.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any

import yaml

SOURCE_GLOB = "test_*.py"
SOURCE_DIR = "tests"
WIDTH = 140
FUTURE = "__future__"

# Where a ``Path(__file__)`` expression of a test file points to, and the constant of ``tests/testkit`` that stands for it. The old places
# of the support modules are listed too: the same expressions were spelled with them before the modules moved into ``tests/testkit/``.
TESTKIT_ANCHORS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("tests", "testkit", "fake_team_agent.py"), "FAKE_TEAM_AGENT"),
    (("tests", "fake_team_agent.py"), "FAKE_TEAM_AGENT"),
    (("tests", "testkit", "fake_agent.py"), "FAKE_AGENT"),
    (("tests", "fake_agent.py"), "FAKE_AGENT"),
    (("tests", "testkit", "expected_dash"), "EXPECTED_DASH"),
    (("tests", "expected_dash"), "EXPECTED_DASH"),
    (("tests",), "TESTS"),
    ((), "REPO"),
)


class ManifestError(Exception):
    """The manifest file cannot be read as a manifest."""


class RelocationError(Exception):
    """A move that cannot be done; ``errors`` lists everything wrong (nothing has been written)."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


# ----------------------------------------------------------------------------------------------------------------------------------
# the manifest


@dataclass(frozen=True)
class Entry:
    """One test of one source, assigned to one destination; ``collected`` is the number of pytest items it makes (parametrize)."""

    source: str
    test: str
    destination: str
    group: str
    collected: int


@dataclass(frozen=True)
class Destination:
    path: str
    group: str
    sources: Mapping[str, tuple[tuple[str, int], ...]]  # source path -> ((test id, collected), ...)

    def entries(self) -> Iterator[Entry]:
        for source, tests in self.sources.items():
            for test, collected in tests:
                yield Entry(source, test, self.path, self.group, collected)


@dataclass(frozen=True)
class Manifest:
    groups: Mapping[str, tuple[str, ...]]  # group -> the places (package names, or ``tests/<dir>``) whose destinations belong to it
    destinations: Mapping[str, Destination]
    duplicates: tuple[str, ...] = ()

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> Manifest:
        if not isinstance(data, Mapping) or data.get("version") != 1:
            raise ManifestError("the manifest must be a mapping with `version: 1`")
        groups_raw = data.get("groups", {})
        destinations_raw = data.get("destinations", {})
        if not isinstance(groups_raw, Mapping) or not isinstance(destinations_raw, Mapping):
            raise ManifestError("`groups` and `destinations` must be mappings")
        groups = {str(g): tuple(str(p) for p in places) for g, places in groups_raw.items()}
        destinations: dict[str, Destination] = {}
        duplicates: list[str] = []
        seen: dict[tuple[str, str], str] = {}
        for path, spec in destinations_raw.items():
            if not isinstance(spec, Mapping) or "group" not in spec or not isinstance(spec.get("sources"), Mapping):
                raise ManifestError(f"{path}: expected `group:` and `sources:`")
            sources: dict[str, tuple[tuple[str, int], ...]] = {}
            for source, tests in spec["sources"].items():
                parsed: list[tuple[str, int]] = []
                for item in tests:
                    name, collected = _entry(path, source, item)
                    parsed.append((name, collected))
                    if (source, name) in seen:
                        duplicates.append(f"{source}::{name} is named twice: by {seen[(source, name)]} and by {path}")
                    seen[(source, name)] = path
                sources[str(source)] = tuple(parsed)
            destinations[str(path)] = Destination(str(path), str(spec["group"]), sources)
        return Manifest(groups, destinations, tuple(duplicates))

    def tests(self) -> list[Entry]:
        return [entry for destination in self.destinations.values() for entry in destination.entries()]

    def assignments(self) -> dict[tuple[str, str], Entry]:
        return {(entry.source, entry.test): entry for entry in self.tests()}

    def group_of_place(self, place: str) -> str | None:
        for group, places in self.groups.items():
            if place in places:
                return group
        return None

    def problems(self) -> list[str]:
        """Everything wrong with the manifest itself (no source is read): doubles, destinations in no group or in the wrong one."""
        found = list(self.duplicates)
        for path, destination in sorted(self.destinations.items()):
            place = place_of(path)
            if place is None:
                found.append(f"{path}: a destination is src/orgmcp/<package>/tests/test_*.py or tests/<dir>/test_*.py")
                continue
            expected = self.group_of_place(place)
            if expected is None:
                found.append(f"{path}: {place!r} is in no group (the `groups:` of the manifest)")
            elif expected != destination.group:
                found.append(f"{path}: group {destination.group!r} is not the group of {place!r} ({expected!r})")
            for source in destination.sources:
                if not _is_source(source):
                    found.append(f"{path}: {source} is not a tests/{SOURCE_GLOB} file")
        return found


def _entry(path: object, source: object, item: object) -> tuple[str, int]:
    if isinstance(item, str):
        return item, 1
    if isinstance(item, Mapping) and len(item) == 1:
        ((name, collected),) = item.items()
        if isinstance(name, str) and isinstance(collected, int) and collected >= 1:
            return name, collected
    raise ManifestError(f"{path}: {source}: a test is `name` or `name: <collected>`, not {item!r}")


def _is_source(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return len(parts) == 2 and parts[0] == SOURCE_DIR and PurePosixPath(path).match(SOURCE_GLOB)


def place_of(destination: str) -> str | None:
    """``src/orgmcp/<package>/tests/test_x.py`` -> ``<package>``; ``tests/<dir>/test_x.py`` -> ``tests/<dir>``; anything else None."""
    parts = PurePosixPath(destination).parts
    if not parts or not PurePosixPath(destination).match(SOURCE_GLOB):
        return None
    if len(parts) == 5 and parts[:2] == ("src", "orgmcp") and parts[3] == "tests":
        return parts[2]
    if len(parts) == 3 and parts[0] == SOURCE_DIR:
        return f"{parts[0]}/{parts[1]}"
    return None


# What the import contracts forbid a test of package P to import (ARCHITECTURE.md 8.2): another orgmcp package that P does not depend on, a
# private module of another package, and the frameworks outside their entry points. A moved test that does so imports the module as
# ``testkit.legacy.<module>`` instead: the same module object (tests/testkit/legacy), invisible to the contracts. The graph is read from
# ``tests/architecture/graph.py`` of the repository; without it nothing is redirected.
LEGACY = "testkit.legacy"
EXTERNAL_HOMES: Mapping[str, frozenset[str]] = {
    "yaml": frozenset({"kernel", "blueprint"}), "mcp": frozenset({"mcp_server"}), "anyio": frozenset({"mcp_server"}),
    "textual": frozenset({"dashboard"}),
}
FACADES = frozenset({"core", "server"})  # orgmcp.core and orgmcp.server: top layer, no package below may import them


@dataclass(frozen=True)
class Rules:
    """For each package: the packages it may import."""

    allowed: Mapping[str, frozenset[str]]
    flat: frozenset[str] = frozenset()  # the flat legacy modules of src/orgmcp (core, server, observe ...): they import the facade and the composition root

    def redirects(self, place: str | None, module: str) -> bool:
        """Whether ``place`` (a package name; None for a destination outside src/orgmcp) must import ``module`` through ``testkit.legacy``."""
        if place is None or place not in self.allowed:
            return False
        parts = module.split(".")
        if parts[0] in EXTERNAL_HOMES:
            return place not in EXTERNAL_HOMES[parts[0]]
        if parts[0] != "orgmcp" or len(parts) < 2:
            return False
        package = parts[1]
        if package == place:
            return False
        if package not in self.allowed and package not in FACADES and package not in self.flat and package != "app":
            return False  # a module the contracts know nothing about
        return package not in self.allowed[place] or any(part.startswith("_") for part in parts[2:])


def load_rules(root: Path) -> Rules | None:
    graph = root / "tests" / "architecture" / "graph.py"
    if not graph.is_file():
        return None
    namespace: dict[str, Any] = {"__name__": "relocate_graph"}
    sys.modules.setdefault("relocate_graph", ModuleType("relocate_graph"))
    exec(compile(graph.read_text(encoding="utf-8"), str(graph), "exec"), namespace)  # noqa: S102 - the repository's own, dependency-free module
    allowed = {name: frozenset(namespace["allowed_imports"](name)) for name in namespace["PACKAGES"]}
    flat = frozenset(p.stem for p in (root / "src" / "orgmcp").glob("*.py") if p.stem not in ("__init__", "__main__"))
    return Rules(allowed, flat)


class _UniqueKeyLoader(yaml.SafeLoader):  # type: ignore[misc]  # PyYAML has no stubs: its classes are Any
    """SafeLoader that refuses a repeated mapping key (PyYAML would silently keep the last one and lose tests)."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        seen: set[object] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise ManifestError(f"duplicate key {key!r} (line {key_node.start_mark.line + 1})")
            seen.add(key)
        mapping: dict[Any, Any] = super().construct_mapping(node, deep)
        return mapping


def load_manifest(path: Path) -> Manifest:
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)  # noqa: S506 - SafeLoader subclass
    except yaml.YAMLError as error:
        raise ManifestError(f"{path}: {error}") from error
    return Manifest.from_dict(data)


# ----------------------------------------------------------------------------------------------------------------------------------
# a module, cut into the statements it is made of


@dataclass(frozen=True, order=True)
class ImportInfo:
    """One name an import statement binds."""

    kind: str  # "import" or "from"
    module: str
    name: str  # the imported name of a ``from`` import ("" for ``import``)
    asname: str | None = None
    level: int = 0

    @property
    def binding(self) -> str:
        if self.asname:
            return self.asname
        return self.name if self.kind == "from" else self.module.split(".")[0]

    @property
    def section(self) -> int:
        if self.kind == "from" and self.module == FUTURE:
            return 0
        top = self.module.split(".")[0]
        if self.level > 0:
            return 4
        if top in sys.stdlib_module_names:
            return 1
        return 3 if top == "orgmcp" else 2


def _alias(info: ImportInfo) -> str:
    base = info.name if info.kind == "from" else info.module
    return f"{base} as {info.asname}" if info.asname else base


def render_imports(infos: Iterable[ImportInfo]) -> list[str]:
    """isort-style lines: future / stdlib / third party (test helper modules included) / orgmcp; plain imports before ``from`` imports."""
    lines: list[str] = []
    for section in range(5):
        group = sorted({i for i in infos if i.section == section}, key=lambda i: (i.kind != "import", i.level, i.module.lower(), i.module))
        block: list[str] = []
        done: set[tuple[str, int]] = set()
        for info in group:
            if info.kind == "import":
                block.append(f"import {_alias(info)}")
                continue
            key = (info.module, info.level)
            if key in done:
                continue
            done.add(key)
            names = sorted({_alias(i) for i in group if i.kind == "from" and (i.module, i.level) == key}, key=_name_order)
            block.extend(_from_line("." * info.level + info.module, names))
        if block:
            lines += ([""] if lines else []) + block
    return lines


def _name_order(alias: str) -> tuple[int, str]:
    name = alias.split(" as ")[0]
    kind = 0 if name.isupper() and len(name) > 1 else 1 if name[:1].isupper() else 2
    return kind, name.lower()


def _from_line(module: str, names: list[str]) -> list[str]:
    line = f"from {module} import {', '.join(names)}"
    if len(line) <= WIDTH:
        return [line]
    return [f"from {module} import (", *[f"    {n}," for n in names], ")"]


@dataclass
class Unit:
    """One statement of a block (the module, or the body of a class) with the lines that belong to it.

    ``lead`` are the comment lines between the previous statement and this one, ``body`` is the statement itself, decorators included.
    Blank lines are not kept: they are written back by ``blanks`` from the kinds of the neighbours, so that what a file looks like after a
    prune depends on the units that are kept only, however many prunes it took.
    """

    index: int
    node: ast.stmt
    kind: str  # doc future import def class assign test testclass method member other
    lead: list[str]
    body: list[str]
    start: int  # 1-based first line of the body
    defines: tuple[str, ...] = ()
    fixture: str | None = None
    autouse: bool = False
    tests: tuple[str, ...] = ()  # ids of the tests the unit holds ("name", or "Class::name" for the methods of a test class)
    members: list[Unit] = field(default_factory=list)
    header: list[str] = field(default_factory=list)  # the lines of a class up to its first member
    infos: tuple[ImportInfo, ...] = ()

    @property
    def is_block(self) -> bool:
        return self.kind in ("def", "class", "test", "testclass", "method", "other")

    @property
    def shape(self) -> Shape:
        if self.kind in ("import", "future"):
            return Shape(self.kind, self.infos[0].section, self.infos[-1].section)
        return Shape(self.kind if self.kind in ("doc", "assign") else "block")


def _is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def _decorators(node: ast.stmt) -> list[ast.expr]:
    found: list[ast.expr] = getattr(node, "decorator_list", [])
    return found


def _first_line(node: ast.stmt) -> int:
    return min([node.lineno, *[d.lineno for d in _decorators(node)]])


def _targets(target: ast.expr) -> Iterator[str]:
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            yield from _targets(element)
    elif isinstance(target, ast.Starred):
        yield from _targets(target.value)


def _decorator_call(decorator: ast.expr) -> ast.expr:
    return decorator.func if isinstance(decorator, ast.Call) else decorator


def _fixture_decorator(node: ast.stmt) -> ast.expr | None:
    for decorator in _decorators(node):
        target = _decorator_call(decorator)
        if (isinstance(target, ast.Name) and target.id == "fixture") or (isinstance(target, ast.Attribute) and target.attr == "fixture"):
            return decorator
    return None


def _fixture_info(node: ast.stmt) -> tuple[str | None, bool]:
    """(the name the fixture is known by, whether it is autouse) of a fixture function; (None, False) for any other statement."""
    decorator = _fixture_decorator(node)
    if decorator is None:
        return None, False
    name = getattr(node, "name", None)
    autouse = False
    if isinstance(decorator, ast.Call):
        for keyword in decorator.keywords:
            if keyword.arg == "name" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                name = keyword.value.value
            if keyword.arg == "autouse":
                autouse = not (isinstance(keyword.value, ast.Constant) and keyword.value.value is False)
    return name, autouse


def _import_infos(node: ast.Import | ast.ImportFrom) -> tuple[ImportInfo, ...]:
    if isinstance(node, ast.Import):
        return tuple(ImportInfo("import", a.name, "", a.asname) for a in node.names)
    return tuple(ImportInfo("from", node.module or "", a.name, a.asname, node.level) for a in node.names)


def _is_test_function(node: ast.stmt) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test") and _fixture_decorator(node) is None


def _is_test_class(node: ast.stmt) -> bool:
    return (isinstance(node, ast.ClassDef) and node.name.startswith("Test")
            and not any(isinstance(m, ast.FunctionDef) and m.name == "__init__" for m in node.body))


class Module:
    """A parsed Python file: its units, the names they define and the tests in it."""

    def __init__(self, path: str, text: str, *, strict: bool = True) -> None:
        self.path = path
        self.text = text
        self.errors: list[str] = []
        self.lines = text.split("\n")
        if self.lines and self.lines[-1] == "":
            self.lines.pop()
        self.tree = ast.parse(text, filename=path)
        self.parents: dict[ast.AST, ast.AST] = {child: parent for parent in ast.walk(self.tree) for child in ast.iter_child_nodes(parent)}
        self.units = self._split(self.tree.body, 0, strict=strict, top=True)
        last_end = self.tree.body[-1].end_lineno if self.tree.body else 0
        self.tail = self.lines[last_end or 0:]
        self.defs: dict[str, list[Unit]] = {}
        self.fixtures: dict[str, list[Unit]] = {}
        self.bindings: dict[str, ImportInfo] = {}
        for unit in self.units:
            for name in unit.defines:
                self.defs.setdefault(name, []).append(unit)
            if unit.fixture:
                self.fixtures.setdefault(unit.fixture, []).append(unit)
            for info in unit.infos:
                self.bindings[info.binding] = info
        self.test_ids = [t for unit in self.units for t in unit.tests]
        self.test_units = {t: unit for unit in self.units for t in unit.tests}

    # -- cutting -------------------------------------------------------------------------------------------------------------------

    def _split(self, statements: list[ast.stmt], after: int, *, strict: bool, top: bool, owner: str = "") -> list[Unit]:
        units: list[Unit] = []
        previous_end = after
        for index, node in enumerate(statements):
            start = _first_line(node)
            if start <= previous_end:
                self.errors.append(f"{self.path}:{node.lineno}: two statements on one line are not supported")
            lead = [line for line in self.lines[previous_end:start - 1] if line.strip() != ""]
            unit = Unit(index, node, "other", lead, self.lines[start - 1:node.end_lineno], start)
            self._classify(unit, node, strict=strict, top=top, first=index == 0, owner=owner)
            units.append(unit)
            previous_end = node.end_lineno or node.lineno
        return units

    def _classify(self, unit: Unit, node: ast.stmt, *, strict: bool, top: bool, first: bool, owner: str) -> None:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            unit.infos = _import_infos(node)
            unit.kind = "future" if isinstance(node, ast.ImportFrom) and node.module == FUTURE and node.level == 0 else "import"
            unit.defines = tuple(i.binding for i in unit.infos)
            if any(a.name == "*" for a in node.names):
                self.errors.append(f"{self.path}:{node.lineno}: `import *` is not supported")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            unit.defines = (node.name,)
            unit.fixture, unit.autouse = _fixture_info(node)
            unit.kind = "def"
            if _is_test_function(node) and (top or owner.startswith("Test")):
                unit.kind = "test" if top else "method"
                unit.tests = (node.name if top else f"{owner}::{node.name}",)
        elif isinstance(node, ast.ClassDef):
            unit.defines = (node.name,)
            unit.kind = "class"
            self._cut_class(unit, node, strict=strict, top=top)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [n for t in targets for n in _targets(t)]
            if top and strict and (not names or len(names) != sum(1 for _ in _walk_targets(targets))):
                self.errors.append(f"{self.path}:{node.lineno}: an assignment to something other than names is not supported")
            unit.defines = tuple(names)
            unit.kind = "assign"
        elif first and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            unit.kind = "doc"
        elif top and strict:
            self.errors.append(f"{self.path}:{node.lineno}: unsupported top-level statement {type(node).__name__}")

    def _cut_class(self, unit: Unit, node: ast.ClassDef, *, strict: bool, top: bool) -> None:
        if not node.body:
            return
        first_start = _first_line(node.body[0])
        header_end = first_start - 1
        while header_end > node.lineno and (self.lines[header_end - 1].strip() == "" or _is_comment(self.lines[header_end - 1])):
            header_end -= 1
        if first_start <= node.lineno or header_end < node.lineno:
            if strict and top:
                self.errors.append(f"{self.path}:{node.lineno}: a class whose body starts on the line of its header is not supported")
            return
        unit.header = self.lines[unit.start - 1:header_end]
        unit.members = self._split(node.body, header_end, strict=False, top=False, owner=node.name)
        if _is_test_class(node) and top:
            unit.kind = "testclass"
            unit.tests = tuple(t for m in unit.members for t in m.tests)

    # -- what a unit needs -----------------------------------------------------------------------------------------------------------

    def nodes_of(self, unit: Unit, selected: frozenset[str] | None) -> list[ast.AST]:
        """The syntax a unit consists of; of a test class only the members that are not tests plus the selected tests."""
        if unit.kind != "testclass" and not (unit.kind == "class" and selected is not None):
            return [unit.node]
        node = unit.node
        assert isinstance(node, ast.ClassDef)
        nodes: list[ast.AST] = [*node.decorator_list, *node.bases, *node.keywords]
        nodes += [m.node for m in unit.members if not m.tests or m.tests[0] in (selected if selected is not None else m.tests)]
        return nodes

    def needs(self, unit: Unit, selected: frozenset[str] | None) -> set[str]:
        """The module-level names (and fixture names) a unit refers to."""
        nodes = self.nodes_of(unit, selected)
        names: set[str] = set()
        words: set[str] = set()
        for root in nodes:
            for node in ast.walk(root):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    names.add(node.id)
                elif isinstance(node, ast.arg):
                    words.add(node.arg)
                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    words.add(node.value)
        return names | (words & set(self.fixtures))

    def closure(self, roots: Iterable[Unit], selected: Mapping[int, frozenset[str]]) -> tuple[list[Unit], list[str]]:
        """The units (not imports) the roots need, in source order, and the tests among them that are not roots (an error for the caller)."""
        root_ids = {u.index for u in roots}
        needed: dict[int, Unit] = {}
        stack = list(roots)
        strangers: list[str] = []
        while stack:
            unit = stack.pop()
            if unit.index in needed:
                continue
            needed[unit.index] = unit
            if unit.index not in root_ids and unit.tests:
                strangers.append(f"{unit.defines[0]}")
            for name in self.needs(unit, selected.get(unit.index)):
                for definition in self.defs.get(name, []):
                    if definition.kind not in ("import", "future") and definition.index != unit.index:
                        stack.append(definition)
                for definition in self.fixtures.get(name, []):
                    if definition.index != unit.index:
                        stack.append(definition)
        return [needed[i] for i in sorted(needed)], sorted(set(strangers))

    def select(self, test_ids: Iterable[str]) -> tuple[list[Unit], dict[int, frozenset[str]]]:
        """The units that hold these tests and, for a test class, which of its methods."""
        chosen: dict[int, set[str]] = {}
        for test_id in test_ids:
            unit = self.test_units[test_id]
            chosen.setdefault(unit.index, set()).add(test_id)
        selected = {i: frozenset(ids) for i, ids in chosen.items() if self.units[i].kind == "testclass"}
        return [self.units[i] for i in sorted(chosen)], selected

    def standing_roots(self) -> list[Unit]:
        """Units that apply to every test of the module: autouse fixtures, ``pytestmark``, pytest hooks."""
        return [u for u in self.units if u.autouse or "pytestmark" in u.defines or any(n.startswith("pytest_") for n in u.defines)]

    # -- ``__file__`` ----------------------------------------------------------------------------------------------------------------

    def file_rewrites(self, nodes: Iterable[ast.AST]) -> tuple[dict[int, list[tuple[int, int, str]]], list[str]]:
        """Replacements (line -> [(first byte, last byte, text)]) of the ``Path(__file__)`` expressions in ``nodes``, and the errors."""
        edits: dict[int, list[tuple[int, int, str]]] = {}
        errors: list[str] = []
        for root in nodes:
            for node in ast.walk(root):
                if not (isinstance(node, ast.Name) and node.id == "__file__"):
                    continue
                where = f"{self.path}:{node.lineno}"
                outcome = self._file_expression(node)
                if isinstance(outcome, str):
                    errors.append(f"{where}: {outcome}")
                    continue
                target, replacement = outcome
                if target.lineno != target.end_lineno or target.end_col_offset is None:
                    errors.append(f"{where}: a `__file__` expression over several lines is not supported")
                    continue
                edits.setdefault(target.lineno, []).append((target.col_offset, target.end_col_offset, replacement))
        return edits, errors

    def import_rewrites(self, nodes: Iterable[ast.AST], place: str | None, rules: Rules | None) -> tuple[dict[int, list[tuple[int, int, str]]], list[str]]:
        """Replacements of the imports inside the statements ``nodes`` (inside a test, say) that the contracts forbid in package ``place``."""
        edits: dict[int, list[tuple[int, int, str]]] = {}
        errors: list[str] = []
        if rules is None or place is None:
            return edits, errors
        for root in nodes:
            for node in ast.walk(root):
                if not isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                outcome = redirected_statement(node, place, rules)
                if outcome is None:
                    continue
                where = f"{self.path}:{node.lineno}"
                if isinstance(outcome, str) and outcome.startswith("!"):
                    errors.append(f"{where}: {outcome[1:]}")
                elif node.lineno != node.end_lineno or node.end_col_offset is None:
                    errors.append(f"{where}: an import over several lines inside a test cannot be redirected")
                else:
                    edits.setdefault(node.lineno, []).append((node.col_offset, node.end_col_offset, outcome.replace("\n", "\n" + " " * node.col_offset)))
        return edits, errors

    def _file_expression(self, name: ast.Name) -> tuple[ast.expr, str] | str:
        call = self.parents.get(name)
        if not (isinstance(call, ast.Call) and call.args == [name] and not call.keywords and _is_path(call.func)):
            return "`__file__` is used other than as Path(__file__)...: the tool cannot rewrite it"
        parts = list(PurePosixPath(self.path).parts)
        current: ast.expr = call
        while True:
            parent = self.parents.get(current)
            if isinstance(parent, ast.Attribute) and parent.value is current:
                outer = self.parents.get(parent)
                if parent.attr == "parent":
                    if not parts:
                        return "`__file__` goes above the repository root"
                    parts.pop()
                    current = parent
                    continue
                if parent.attr in ("resolve", "with_name", "parents") and isinstance(outer, (ast.Call, ast.Subscript)):
                    if parent.attr == "resolve" and isinstance(outer, ast.Call) and outer.func is parent and not outer.args and not outer.keywords:
                        current = outer
                        continue
                    if (parent.attr == "with_name" and isinstance(outer, ast.Call) and outer.func is parent and len(outer.args) == 1
                            and not outer.keywords and isinstance(outer.args[0], ast.Constant) and isinstance(outer.args[0].value, str)):
                        if not parts:
                            return "`__file__` goes above the repository root"
                        parts[-1] = outer.args[0].value
                        current = outer
                        continue
                    if (parent.attr == "parents" and isinstance(outer, ast.Subscript) and outer.value is parent
                            and isinstance(outer.slice, ast.Constant) and isinstance(outer.slice.value, int) and outer.slice.value >= 0):
                        if len(parts) < outer.slice.value + 1:
                            return "`__file__` goes above the repository root"
                        del parts[len(parts) - outer.slice.value - 1:]
                        current = outer
                        continue
                break
            if (isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Div) and parent.left is current
                    and isinstance(parent.right, ast.Constant) and isinstance(parent.right.value, str)):
                parts += [p for p in parent.right.value.split("/") if p]
                current = parent
                continue
            break
        if len(parts) == 2 and parts[0] == SOURCE_DIR and PurePosixPath(parts[1]).match(SOURCE_GLOB):
            return f"`__file__` points at a test file ({'/'.join(parts)}), which moves: the tool cannot rewrite it"
        for anchor, constant in TESTKIT_ANCHORS:
            if tuple(parts[:len(anchor)]) == anchor:
                rest = parts[len(anchor):]
                text = f"testkit.{constant}" + "".join(f' / "{p}"' for p in rest)
                wrap = bool(rest) and not isinstance(current, ast.BinOp) and self._needs_parentheses(current)  # a BinOp has its parentheses already
                return current, f"({text})" if wrap else text
        return "`__file__` points to a place the tool does not know"

    def _needs_parentheses(self, expression: ast.expr) -> bool:
        parent = self.parents.get(expression)
        if isinstance(parent, (ast.Assign, ast.AnnAssign, ast.keyword, ast.Return, ast.Expr, ast.Tuple, ast.List, ast.Set, ast.Dict)):
            return False
        if isinstance(parent, ast.Call) and expression in parent.args:
            return False
        return not (isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Div) and parent.left is expression)

    # -- rendering ---------------------------------------------------------------------------------------------------------------------

    def render_unit(self, unit: Unit, selected: frozenset[str] | None, edits: Mapping[int, Sequence[tuple[int, int, str]]] | None = None) -> list[str]:
        """The lines of a unit (a test class only with the selected methods), with the ``__file__`` edits applied."""
        edits = edits or {}
        if unit.kind == "testclass" or (unit.kind == "class" and selected is not None):
            keep = [m for m in unit.members if not m.tests or m.tests[0] in (selected if selected is not None else m.tests)]
            lines = self._edit(unit.header, unit.start, edits)
            previous: Unit | None = None
            for member in keep:
                lines += [""] * blanks(previous.shape if previous else None, member.shape, top=False) + member.lead + self._edit(member.body, member.start, edits)
                previous = member
            return unit.lead + lines
        return unit.lead + self._edit(unit.body, unit.start, edits)

    @staticmethod
    def _edit(lines: list[str], first: int, edits: Mapping[int, Sequence[tuple[int, int, str]]]) -> list[str]:
        out = []
        for offset, line in enumerate(lines):
            raw = line.encode()
            for begin, end, text in sorted(edits.get(first + offset, ()), reverse=True):
                raw = raw[:begin] + text.encode() + raw[end:]
            out.append(raw.decode())
        return out


@dataclass(frozen=True)
class Shape:
    """What decides the blank lines around a statement: its kind and, for an import, its section."""

    kind: str  # doc future import assign block
    first: int = 0
    last: int = 0


def blanks(previous: Shape | None, following: Shape, *, top: bool = True) -> int:
    """How many blank lines separate two kept statements: a function of their shapes only (never of the lines they had before)."""
    if previous is None:
        return 0
    if not top:
        return 0 if previous.kind == "assign" and following.kind == "assign" else 1
    if previous.kind == "doc":
        return 1
    if previous.kind == "future":
        return 0 if following.kind == "future" else 1
    if previous.kind == "import":
        if following.kind in ("import", "future"):
            return 0 if previous.last == following.first else 1
        return 2 if following.kind == "block" else 1
    if previous.kind == "assign":
        return 0 if following.kind == "assign" else 2 if following.kind == "block" else 1
    return 2


def redirected_statement(node: ast.Import | ast.ImportFrom, place: str, rules: Rules) -> str | None:
    """The text that replaces an import statement the contracts forbid in package ``place``; None if it is fine; ``!reason`` if it cannot be done."""
    if isinstance(node, ast.Import):
        if not any(rules.redirects(place, a.name) for a in node.names):
            return None
        if any(a.asname is None and "." in a.name for a in node.names if rules.redirects(place, a.name)):
            return "!`import a.b` without `as` of a module the contracts forbid here cannot be redirected: write `import a.b as <name>`"
        return "\n".join(f"import {LEGACY}.{a.name} as {a.asname or a.name}" if rules.redirects(place, a.name) else _plain(a) for a in node.names)
    if node.level or node.module is None:
        return None
    module = node.module
    if module == "orgmcp":
        away = [a for a in node.names if rules.redirects(place, f"orgmcp.{a.name}")]
        if not away:
            return None
        stay = [a for a in node.names if a not in away]
        lines = [f"from {LEGACY}.orgmcp import {', '.join(_alias_text(a) for a in away)}"]
        if stay:
            lines.insert(0, f"from orgmcp import {', '.join(_alias_text(a) for a in stay)}")
        return "\n".join(lines)
    if not rules.redirects(place, module):
        return None
    return f"from {LEGACY}.{module} import {', '.join(_alias_text(a) for a in node.names)}"


def _alias_text(alias: ast.alias) -> str:
    return f"{alias.name} as {alias.asname}" if alias.asname else alias.name


def _plain(alias: ast.alias) -> str:
    return f"import {_alias_text(alias)}"


def _walk_targets(targets: Sequence[ast.expr]) -> Iterator[ast.expr]:
    for target in targets:
        if isinstance(target, (ast.Tuple, ast.List)):
            yield from _walk_targets(target.elts)
        elif isinstance(target, ast.Starred):
            yield from _walk_targets([target.value])
        else:
            yield target


def _is_path(func: ast.expr) -> bool:
    return (isinstance(func, ast.Name) and func.id == "Path") or (
        isinstance(func, ast.Attribute) and func.attr == "Path" and isinstance(func.value, ast.Name) and func.value.id == "pathlib")


def loaded_names(nodes: Iterable[ast.AST]) -> set[str]:
    return {n.id for root in nodes for n in ast.walk(root) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def _join(lines: Sequence[str]) -> str:
    return "\n".join(lines).rstrip("\n") + "\n"


# ----------------------------------------------------------------------------------------------------------------------------------
# the source side: what is left of a module when some of its tests are gone


def prune_module(module: Module, removed: set[str]) -> str | list[str]:
    """The text of ``module`` without the tests ``removed`` and without everything nothing needs any more; the errors if it cannot be done.

    The result depends on the tests that are left only: it keeps what is reachable from them (and the standing units), the imports they
    use, the docstring and the ``__future__`` imports. A module with no test left is deleted: the empty string.
    """
    remaining = [t for t in module.test_ids if t not in removed]
    if not remaining:
        return ""
    roots, selected = module.select(remaining)
    kept, _ = module.closure([*roots, *module.standing_roots()], selected)
    gone = {u.defines[0] for u in module.units if u.tests and all(t in removed for t in u.tests)}
    errors = [f"{module.path}: {unit.defines[0]} still uses {name}, which moves away"
              for unit in kept if unit.defines for name in sorted(module.needs(unit, selected.get(unit.index)) & gone)]
    if errors:
        return errors
    kept_ids = {u.index for u in kept}
    used = loaded_names(n for u in kept for n in module.nodes_of(u, selected.get(u.index)))
    out: list[str] = []
    previous: Shape | None = None
    for unit in module.units:
        shape = unit.shape
        if unit.kind in ("doc", "future"):
            lines = unit.lead + unit.body
        elif unit.kind == "import":
            kept_infos = [i for i in unit.infos if i.binding in used or "noqa" in "\n".join(unit.body)]
            if not kept_infos:
                continue
            lines = unit.lead + (unit.body if len(kept_infos) == len(unit.infos) else render_imports(kept_infos))
            shape = Shape("import", kept_infos[0].section, kept_infos[-1].section)
        elif unit.index in kept_ids:
            lines = module.render_unit(unit, selected.get(unit.index))
        else:
            continue
        out += [""] * blanks(previous, shape) + lines
        previous = shape
        if unit.index == module.units[-1].index and any(line.strip() for line in module.tail):
            out += ["", *[line for line in module.tail if line.strip()]]
    return _join(out)


# ----------------------------------------------------------------------------------------------------------------------------------
# the destination side


@dataclass(frozen=True)
class Item:
    """A statement to write into a destination."""

    keys: tuple[str, ...]
    lines: list[str]
    dump: str
    is_test: bool
    shape: Shape
    where: str


@dataclass(frozen=True)
class Part:
    module: Module
    tests: list[str]


def build_destination(path: str, existing: Module | None, parts: Sequence[Part], rules: Rules | None = None) -> str | list[str]:
    """The new text of a destination file that receives the tests of ``parts`` (a new file, or ``existing`` extended), or the errors."""
    place = place_of(path) if path.startswith("src/orgmcp/") else None
    errors: list[str] = []
    items: list[Item] = []
    infos: dict[str, ImportInfo] = {}
    future = False
    taken: dict[str, Item] = {}
    seen: list[Seen] = []
    for part in parts:
        module = part.module
        roots, selected = module.select(part.tests)
        standing = module.standing_roots()
        if any("pytestmark" in u.defines for u in standing) and (existing is not None or len(parts) > 1):
            errors.append(f"{path}: {module.path} has a module-level pytestmark, which cannot be merged into a destination that holds other "
                          "tests: give this source a destination of its own in the manifest")
            continue
        autouse = [u for u in standing if u.autouse]
        if autouse and (existing is not None or len(parts) > 1):
            errors.append(f"{path}: {module.path} has the autouse fixture {autouse[0].defines[0]}, which would apply to the tests of the "
                          "other sources in this destination: give this source a destination of its own in the manifest")
            continue
        if existing is not None and any(u.autouse for u in existing.units):
            errors.append(f"{path}: the destination has an autouse fixture, which would apply to the moved tests: name another destination")
            continue
        needed, strangers = module.closure([*roots, *standing], selected)
        errors += [f"{path}: {module.path}: a moved test uses the test {name}, which must move with it" for name in strangers]
        included = [n for u in needed for n in module.nodes_of(u, selected.get(u.index))]
        edits, problems = module.file_rewrites(included)
        errors += [f"{path}: {p}" for p in problems]
        if existing is not None:
            errors += _captured(path, module, existing, included)
        uses_testkit = bool(edits)
        nested, problems = module.import_rewrites(included, place, rules)
        errors += [f"{path}: {p}" for p in problems]
        for line, found in nested.items():
            edits.setdefault(line, []).extend(found)
        used: set[str] = set()
        for unit in needed:
            lines = module.render_unit(unit, selected.get(unit.index), edits)
            parsed = ast.parse("\n".join(lines) + "\n")
            used |= loaded_names([parsed])
            item = Item(unit.defines or unit.tests, lines, ast.dump(parsed), bool(unit.tests), unit.shape, module.path)
            clash = _clash(item, taken, existing, path)
            if clash is True:
                continue
            if clash:
                errors.append(clash)
                continue
            items.append(item)
            taken.update({key: item for key in item.keys})
        wanted = [_through_legacy(module.bindings[name], place, rules) for name in sorted(used)
                  if name in module.bindings and module.bindings[name].module != FUTURE]
        if uses_testkit:
            wanted.append(ImportInfo("import", "testkit", ""))
        for info in wanted:
            problem = info if isinstance(info, str) else _bind(infos, info, existing, path)
            if problem:
                errors.append(f"{path}: {module.path}: {problem}" if isinstance(info, str) else problem)
        future = future or any(u.kind == "future" for u in module.units)
        seen.append(Seen(module.path, {n.arg for root in included for n in ast.walk(root) if isinstance(n, ast.arg)},
                         loaded_names(included) - set(module.defs) - set(module.bindings), set(module.fixtures),
                         {key: item.dump for item in items if item.where == module.path for key in item.keys},
                         {i.binding for i in wanted if isinstance(i, ImportInfo)}))
    errors += _crossed(path, seen)
    if errors:
        return sorted(set(errors))
    if existing is not None:
        return _extend(existing, items, [i for i in infos.values() if existing.bindings.get(i.binding) != i])
    return _new_file(items, list(infos.values()), future, header=path.startswith("src/orgmcp/"))


@dataclass
class Seen:
    """What one source of a destination asks for and provides, to find the names that would mean something else in the merged module."""

    source: str
    requested: set[str]  # parameter names (fixture requests) of the included functions
    free: set[str]  # names used that the source does not define itself
    fixtures: set[str]  # the fixtures the source defines
    defined: dict[str, str]  # name -> its definition (ast dump), of the statements it contributes
    imported: set[str]  # names it imports


def _crossed(path: str, seen: Sequence[Seen]) -> list[str]:
    """Names that one source of the destination defines or imports and another source gets from elsewhere (conftest, builtins) or means differently."""
    errors = []
    for one in seen:
        for other in seen:
            if one is other:
                continue
            for name in sorted((other.requested & one.fixtures) - other.fixtures):
                errors.append(f"{path}: {other.source} gets the fixture {name!r} from conftest, but {one.source} defines one of that name "
                              "(the module would use it for both): name another destination")
            for name in sorted(other.free & (set(one.defined) | one.imported)):
                if name not in other.requested:
                    errors.append(f"{path}: {other.source} uses {name!r} from elsewhere, but {one.source} defines or imports one of that name: "
                                  "name another destination")
            for name in sorted(one.imported & set(other.defined)):
                errors.append(f"{path}: {name!r} is imported by {one.source} and defined by {other.source}: name another destination")
    return errors


def _captured(path: str, module: Module, existing: Module, nodes: Sequence[ast.AST]) -> list[str]:
    """Names the moved tests use but their source does not define (a conftest fixture, a builtin) that the existing destination does define:
    the tests would silently get the destination's object instead."""
    requested = {n.arg for root in nodes for n in ast.walk(root) if isinstance(n, ast.arg)}
    loaded = loaded_names(nodes)
    clash = {name for name in requested if name in existing.fixtures and name not in module.fixtures}
    clash |= {name for name in loaded if name in existing.defs and name not in module.defs and name not in module.bindings}
    return [f"{path}: {module.path}: the moved tests use {name!r}, which comes from elsewhere (conftest, builtins) there but is defined in the "
            "destination: they would pick up the destination's; name another destination in the manifest" for name in sorted(clash)]


def _through_legacy(info: ImportInfo, place: str | None, rules: Rules | None) -> ImportInfo | str:
    """The import a destination of package ``place`` writes for ``info``: through ``testkit.legacy`` if the contracts forbid the original."""
    if rules is None or place is None or info.level:
        return info
    if info.kind == "from" and info.module == "orgmcp":
        if rules.redirects(place, f"orgmcp.{info.name}"):
            return ImportInfo("from", f"{LEGACY}.orgmcp", info.name, info.asname)
        return info
    if rules.redirects(place, info.module):
        if info.kind == "import":
            if info.asname is None and "." in info.module:
                return f"`import {info.module}` is forbidden in package {place} and cannot be redirected without `as`: write `import {info.module} as <name>`"
            return ImportInfo("import", f"{LEGACY}.{info.module}", "", info.asname or info.module)
        return ImportInfo("from", f"{LEGACY}.{info.module}", info.name, info.asname)
    return info


def _bind(infos: dict[str, ImportInfo], info: ImportInfo, existing: Module | None, path: str) -> str | None:
    other = infos.get(info.binding)
    if other is not None and other != info:
        return f"{path}: the name {info.binding!r} is imported two ways ({other.module} {other.name} and {info.module} {info.name})"
    if existing is not None:
        there = existing.bindings.get(info.binding)
        if there is not None and there != info:
            return f"{path}: the name {info.binding!r} is imported differently in the destination"
        if info.binding in existing.defs and there is None:
            return f"{path}: the name {info.binding!r} is defined in the destination but imported by the moved tests"
    infos[info.binding] = info
    return None


def _clash(item: Item, taken: Mapping[str, Item], existing: Module | None, path: str) -> str | bool | None:
    """None: no clash; True: the same statement is there already (a shared helper); a message: a clash that is an error."""
    for key in item.keys:
        before = taken.get(key)
        there = existing.defs.get(key) if existing is not None else None
        if item.is_test:
            if before is not None or there:
                return f"{path}: the test {key} is already defined there (moving {item.where}); name another destination in the manifest"
            continue
        if before is not None:
            if before.dump == item.dump:
                return True
            return f"{path}: the helper {key} differs between {before.where} and {item.where}; they cannot share a destination"
        if there:
            same = there[0].kind != "import" and ast.dump(ast.parse("\n".join(there[0].body) + "\n")) == item.dump
            if same:
                return True
            return f"{path}: {key} is defined differently in the destination (moving {item.where}); name another destination in the manifest"
        if existing is not None and key in existing.bindings:
            return f"{path}: {key} is imported by the destination and defined by the moved tests ({item.where})"
    return None


MYPY_DEBT = [
    "# mypy: ignore-errors",
    "# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.",
]


def _new_file(items: list[Item], infos: list[ImportInfo], future: bool, *, header: bool = False) -> str:
    lines: list[str] = list(MYPY_DEBT) if header else []
    if future:
        lines += ([""] if lines else []) + ["from __future__ import annotations"]
    block = render_imports(infos)
    if block:
        lines += ([""] if lines else []) + block
    previous = Shape("import", 0, 3) if lines else None
    for item in items:
        lines += [""] * blanks(previous, item.shape) + item.lines
        previous = item.shape
    return _join(lines)


def _extend(existing: Module, items: list[Item], infos: list[ImportInfo]) -> str:
    lines = list(existing.lines)
    inserts: list[tuple[int, int, list[str]]] = []  # (after this line, section, lines)
    units = [u for u in existing.units if u.kind in ("import", "future")]
    for section in sorted({i.section for i in infos}):
        block = render_imports([i for i in infos if i.section == section])
        same = [u for u in units if u.infos[0].section == section]
        lower = [u for u in units if u.infos[0].section < section]
        if same:
            inserts.append((same[-1].node.end_lineno or 0, section, block))
        elif lower:
            inserts.append((lower[-1].node.end_lineno or 0, section, ["", *block]))
        elif units:
            inserts.append((units[0].start - 1 - len(units[0].lead), section, [*block, ""]))
        else:
            doc = existing.units[0] if existing.units and existing.units[0].kind == "doc" else None
            inserts.append((doc.node.end_lineno or 0 if doc else 0, section, (["", *block] if doc else [*block, ""])))
    for after, _, block in sorted(inserts, key=lambda t: (t[0], t[1]), reverse=True):
        lines[after:after] = block
    while lines and lines[-1].strip() == "":
        lines.pop()
    previous = existing.units[-1].shape if existing.units else None
    for item in items:
        lines += [""] * blanks(previous, item.shape) + item.lines
        previous = item.shape
    return _join(lines)


# ----------------------------------------------------------------------------------------------------------------------------------
# a run over the repository


@dataclass(frozen=True)
class Change:
    path: str
    text: str | None  # None: the file is deleted


class Repo:
    """The sources and destinations of a repository, parsed once."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._modules: dict[str, Module | None] = {}

    def module(self, path: str, *, strict: bool = True) -> Module | None:
        key = f"{path}|{strict}"
        if key not in self._modules:
            file = self.root / path
            self._modules[key] = Module(path, file.read_text(encoding="utf-8"), strict=strict) if file.is_file() else None
        return self._modules[key]

    def sources(self) -> list[str]:
        return sorted(p.relative_to(self.root).as_posix() for p in (self.root / SOURCE_DIR).glob(SOURCE_GLOB))


def source_inventory(root: Path) -> dict[str, tuple[str, ...]]:
    """Every ``tests/test_*.py`` of the repository with the ids of its tests."""
    repo = Repo(root)
    inventory: dict[str, tuple[str, ...]] = {}
    for path in repo.sources():
        module = repo.module(path)
        assert module is not None
        inventory[path] = tuple(module.test_ids)
    return inventory


def _group_entries(manifest: Manifest, group: str) -> list[Destination]:
    return [d for _, d in sorted(manifest.destinations.items()) if d.group == group]


def run_group(root: Path, manifest: Manifest, group: str, *, destinations: bool) -> tuple[list[Change], list[str]]:
    """The changes that applying (``destinations=True``) or only pruning a group makes, and the errors; writes nothing."""
    repo = Repo(root)
    rules = load_rules(root)
    errors: list[str] = []
    changes: list[Change] = []
    removals: dict[str, list[str]] = {}
    scheduled_inits: set[str] = set()
    for destination in _group_entries(manifest, group):
        parts: list[Part] = []
        for source, tests in sorted(destination.sources.items()):
            try:
                module = repo.module(source)
            except SyntaxError as error:
                errors.append(f"{source}: {error}")
                continue
            if module is None:
                continue
            errors += module.errors
            present = [name for name, _ in tests if name in module.test_units]
            if present:
                parts.append(Part(module, present))
                removals.setdefault(source, []).extend(present)
        if not destinations or not parts:
            continue
        existing = repo.module(destination.path, strict=False)
        built = build_destination(destination.path, existing, parts, rules)
        if isinstance(built, list):
            errors += built
            continue
        changes.append(Change(destination.path, built))
        init = str(PurePosixPath(destination.path).parent / "__init__.py")
        if not (root / init).is_file() and init not in scheduled_inits:
            scheduled_inits.add(init)
            changes.append(Change(init, ""))
    for source, removed in sorted(removals.items()):
        module = repo.module(source)
        assert module is not None
        pruned = prune_module(module, set(removed))
        if isinstance(pruned, list):
            errors += pruned
        else:
            changes.append(Change(source, None if pruned == "" else pruned))
    return changes, sorted(set(errors))


def _write(root: Path, changes: Sequence[Change]) -> None:
    for change in changes:
        file = root / change.path
        if change.text is None:
            file.unlink()
        elif not file.is_file() or file.read_text(encoding="utf-8") != change.text:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(change.text, encoding="utf-8")


def apply_group(root: Path, manifest: Manifest, group: str, *, dry_run: bool = False) -> list[Change]:
    return _act(root, manifest, group, destinations=True, dry_run=dry_run)


def prune_group(root: Path, manifest: Manifest, group: str, *, dry_run: bool = False) -> list[Change]:
    return _act(root, manifest, group, destinations=False, dry_run=dry_run)


def _act(root: Path, manifest: Manifest, group: str, *, destinations: bool, dry_run: bool) -> list[Change]:
    if group not in manifest.groups:
        raise RelocationError([f"unknown group {group!r} (the manifest has {', '.join(sorted(manifest.groups))})"])
    changes, errors = run_group(root, manifest, group, destinations=destinations)
    if errors:
        raise RelocationError(errors)
    if not dry_run:
        _write(root, changes)
    return changes


# ----------------------------------------------------------------------------------------------------------------------------------
# the plan


@dataclass
class Plan:
    errors: list[str]
    lines: list[str]

    def render(self) -> str:
        return "\n".join(self.lines) + "\n"


def make_plan(root: Path, manifest: Manifest) -> Plan:
    """The dry run: what the manifest assigns to whom, checked against the sources and destinations as they are."""
    errors = manifest.problems()
    repo = Repo(root)
    assigned = manifest.assignments()
    pending: dict[str, int] = {}
    moved: dict[str, int] = {}
    for path in repo.sources():
        try:
            module = repo.module(path)
        except SyntaxError as error:
            errors.append(f"{path}: {error}")
            continue
        assert module is not None
        errors += module.errors
        errors += [f"unassigned test {path}::{test}" for test in module.test_ids if (path, test) not in assigned]
    for entry in manifest.tests():
        try:
            module = repo.module(entry.source)
            there = repo.module(entry.destination, strict=False)
        except SyntaxError as error:
            errors.append(f"{entry.destination}: {error}")
            continue
        if module is not None and entry.test in module.test_units:
            pending[entry.group] = pending.get(entry.group, 0) + 1
        elif there is not None and entry.test in there.test_units:
            moved[entry.group] = moved.get(entry.group, 0) + 1
        else:
            errors.append(f"{entry.source}::{entry.test} is named by {entry.destination} but found nowhere (neither in the source nor there)")
    for place in sorted({p for d in manifest.destinations for p in [place_of(d)] if p and not p.startswith("tests/")}):
        if not (root / "src" / "orgmcp" / place).is_dir():
            errors.append(f"the package src/orgmcp/{place} does not exist")
    for group in sorted(manifest.groups):
        if not any(d.group == group for d in manifest.destinations.values()):
            continue
        try:
            _, problems = run_group(root, manifest, group, destinations=True)
        except SyntaxError as error:
            problems = [str(error)]
        errors += problems
    lines = _summary(root, manifest, pending, moved)
    errors = sorted(set(errors))
    lines += [f"{len(errors)} errors:", *[f"  {e}" for e in errors]] if errors else ["no errors"]
    return Plan(errors, lines)


def _summary(root: Path, manifest: Manifest, pending: Mapping[str, int], moved: Mapping[str, int]) -> list[str]:
    tests = manifest.tests()
    sources = sorted({t.source for t in tests})
    lines = [f"relocation plan: {len(sources)} sources, {len(tests)} tests ({sum(t.collected for t in tests)} collected) "
             f"-> {len(manifest.destinations)} destinations"]
    for group in sorted(manifest.groups):
        mine = [d for _, d in sorted(manifest.destinations.items()) if d.group == group]
        entries = [e for d in mine for e in d.entries()]
        lines.append(f"group {group}: {len(entries)} tests ({sum(e.collected for e in entries)} collected) in {len(mine)} destinations; "
                     f"pending {pending.get(group, 0)}, moved {moved.get(group, 0)}")
        for destination in mine:
            count = sum(len(t) for t in destination.sources.values())
            collected = sum(c for t in destination.sources.values() for _, c in t)
            state = "extends" if (root / destination.path).is_file() else "new"
            origin = ", ".join(f"{s} ({len(t)})" if len(destination.sources) > 1 else s for s, t in destination.sources.items())
            lines.append(f"  {destination.path} ({state}, {count} tests, {collected} collected) <- {origin}")
    return lines


# ----------------------------------------------------------------------------------------------------------------------------------
# command line


def main(argv: Sequence[str] | None = None) -> int:
    default_repo = Path(__file__).resolve().parent.parent
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", type=Path, default=default_repo, help="the repository root (default: the one this tool lives in)")
    common.add_argument("--manifest", type=Path, default=None, help="default: <repo>/tests/architecture/relocation.yaml")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", parents=[common], help="dry run: counts per group and destination, and every error")
    for name, help_text in (("apply", "move the tests of one group"), ("prune", "remove the tests of one group from their sources")):
        sub = commands.add_parser(name, parents=[common], help=help_text)
        sub.add_argument("--group", required=True)
        sub.add_argument("--dry-run", action="store_true", help="say what would change; change nothing")
    args = parser.parse_args(argv)
    root: Path = args.repo
    manifest_path: Path = args.manifest or root / "tests" / "architecture" / "relocation.yaml"
    try:
        manifest = load_manifest(manifest_path)
    except (ManifestError, OSError) as error:
        print(f"error: {error}")
        return 1
    if args.command == "plan":
        plan = make_plan(root, manifest)
        print(plan.render(), end="")
        return 1 if plan.errors else 0
    try:
        changes = (apply_group if args.command == "apply" else prune_group)(root, manifest, args.group, dry_run=args.dry_run)
    except RelocationError as error:
        print(f"{len(error.errors)} errors, nothing was changed:")
        print("\n".join(f"  {e}" for e in error.errors))
        return 1 if args.group in manifest.groups else 2
    written = [c for c in changes if c.text is not None]
    deleted = [c for c in changes if c.text is None]
    verb = "would change" if args.dry_run else "changed"
    print(f"{args.command} group {args.group}: {verb} {len(written)} files, deleted {len(deleted)}")
    for change in changes:
        print(f"  {'delete' if change.text is None else 'write'} {change.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
