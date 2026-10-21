"""The structural checkers of the refactor (ARCHITECTURE.md 1.2 and 8.4), as plain functions over a source tree.

Every checker takes a ``Tree`` (a directory holding a Python package) and returns a list of ``Violation``. They work on the AST, so
they run on ``src/hirearchy`` AND on the seeded violations in ``fixtures/bad_pkg`` without importing either: ``test_architecture.py``
proves that each checker is quiet on the real code and flags the seeded violation. A checker that finds nothing to look at (a package
that does not exist yet) is quiet: the checks are vacuous for packages that are not there.

Rules covered here: R1 (``init_reexports``), R6 (``module_singletons``; the class check itself is ``class_interfaces``), R7
(``protocol_widths``), R8 (``contract_suites``), R9 (``single_writer`` and ``ledger_names``), R13 (``responsibilities``), the package
shape of 2.1 (``package_contents``) and the dependency graph of 2.2/4.3 (``imports_against_graph``). R2-R5 are import-linter contracts
(``gen_importlinter``).
"""

from __future__ import annotations

import ast
import importlib
import re
import sys
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from . import contract_debt, document, graph, ownership

MAX_PROTOCOL_METHODS = 8
WRITE_CALLS = frozenset({"write_text", "write_bytes", "atomic_write", "replace", "rename", "move", "mkdir", "touch", "unlink",
                         "rmdir", "rmtree", "write", "open", "copy", "copyfile", "copytree", "symlink_to", "hardlink_to"})
# Files and directories a package may hold besides __init__.py, api.py, testing.py, tests/ and _*.py.
PACKAGE_DATA: dict[str, tuple[str, ...]] = {
    "blueprint": ("roles",),
    "dashboard": ("*.tcss",),
    "app": ("wiring.py", "runtime.py", "facade.py", "wire_*.py", "fields_*.py"),  # the composition root's public modules (6.1; fields_*: the parts of OrgRuntime, 9.2)
}
MUTABLE_FACTORIES = frozenset({"OrderedDict", "defaultdict", "deque", "Counter", "local", "Lock", "RLock", "dict", "list", "set"})


@dataclass(frozen=True)
class Violation:
    rule: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"[{self.rule}] {self.where}: {self.message}"


@dataclass(frozen=True)
class Module:
    name: str  # dotted, e.g. hirearchy.mail._mailbox
    package: str  # first component below the root ("mail"), "" for modules directly under the root
    path: Path
    ast: ast.Module
    is_package: bool  # an __init__.py


class Tree:
    """A package directory on disk: ``Tree(Path("src/hirearchy"))`` or ``Tree(Path(".../fixtures/bad_pkg"))``."""

    def __init__(self, directory: Path, name: str | None = None) -> None:
        self.directory = directory
        self.name = name or directory.name

    def package_dirs(self) -> list[Path]:
        return sorted(d for d in self.directory.iterdir() if d.is_dir() and (d / "__init__.py").is_file())

    def package_names(self) -> list[str]:
        return [d.name for d in self.package_dirs()]

    def modules(self, *, tests: bool = False, packages_only: bool = True) -> Iterator[Module]:
        """Modules of the packages (not of the flat modules directly under the root: ``core``, ``__main__``; unless ``packages_only=False``)."""
        for path in sorted(self.directory.rglob("*.py")):
            relative = path.relative_to(self.directory)
            parts = relative.with_suffix("").parts
            if "__pycache__" in parts or ("tests" in parts and not tests) or "fixtures" in parts:
                continue
            if packages_only and len(parts) == 1:
                continue
            is_package = parts[-1] == "__init__"
            dotted = ".".join((self.name, *(parts[:-1] if is_package else parts)))
            yield Module(dotted, parts[0] if len(parts) > 1 else "", path, ast.parse(path.read_text(encoding="utf-8")), is_package)


def _where(module: Module, node: ast.AST) -> str:
    return f"{module.name}:{getattr(node, 'lineno', '?')}"


def _snake(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()


def _is_protocol(node: ast.ClassDef) -> bool:
    for base in node.bases:
        target = base.value if isinstance(base, ast.Subscript) else base
        if (isinstance(target, ast.Name) and target.id == "Protocol") or (isinstance(target, ast.Attribute) and target.attr == "Protocol"):
            return True
    return False


# ------------------------------------------------------------------------------------------------------------------- R7


def protocol_widths(tree: Tree, limit: int = MAX_PROTOCOL_METHODS) -> list[Violation]:
    """R7: no Protocol has more than ``limit`` public methods (interface segregation)."""
    found = []
    for module in tree.modules():
        for node in ast.walk(module.ast):
            if isinstance(node, ast.ClassDef) and _is_protocol(node):
                methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                           and not n.name.startswith("_")]
                if len(methods) > limit:
                    found.append(Violation("R7", _where(module, node), f"Protocol {node.name} has {len(methods)} public methods "
                                                                       f"(max {limit}): split it into role interfaces"))
    return found


# ------------------------------------------------------------------------------------------------------------------- R6


def _data_class(node: ast.ClassDef) -> bool:
    """Data, not behaviour: a dataclass / NamedTuple / Enum / TypedDict / exception / Protocol (instances are values)."""
    for deco in node.decorator_list:
        target = deco.func if isinstance(deco, ast.Call) else deco
        if (isinstance(target, ast.Name) and target.id == "dataclass") or (isinstance(target, ast.Attribute) and target.attr == "dataclass"):
            return True
    names = {b.id if isinstance(b, ast.Name) else b.attr if isinstance(b, ast.Attribute) else "" for b in node.bases}
    return bool(names & {"NamedTuple", "Enum", "IntEnum", "StrEnum", "Flag", "TypedDict", "Protocol", "Exception", "BaseException"}) \
        or any(n.endswith(("Error", "Exception")) for n in names)


def _toplevel_assignments(body: list[ast.stmt]) -> Iterator[ast.Assign | ast.AnnAssign]:
    for stmt in body:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            yield stmt
        elif isinstance(stmt, (ast.If, ast.Try, ast.With)):
            inner = [*stmt.body, *getattr(stmt, "orelse", []), *getattr(stmt, "finalbody", [])]
            for handler in getattr(stmt, "handlers", []):
                inner.extend(handler.body)
            yield from _toplevel_assignments(inner)


def module_singletons(tree: Tree, skip: Iterable[str] = ("app",)) -> list[Violation]:
    """R6: outside ``app``, no module-level instance of a class defined in the tree, and no module-level mutable container
    (an empty dict/list/set, ``OrderedDict()``, ``threading.local()``, a lock): state belongs to the composition root.

    Constants, regexes, Protocols, and instances of data classes (dataclass, NamedTuple, Enum, exceptions) are fine."""
    classes: dict[str, ast.ClassDef] = {}
    for module in tree.modules():
        classes.update({n.name: n for n in module.ast.body if isinstance(n, ast.ClassDef)})
    found = []
    for module in tree.modules():
        if module.package in set(skip):
            continue
        for stmt in _toplevel_assignments(module.ast.body):
            value = stmt.value
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            if value is None or any(isinstance(t, ast.Name) and t.id in ("__all__", "__slots__") for t in targets):
                continue
            label = ", ".join(t.id for t in targets if isinstance(t, ast.Name)) or "<target>"
            if isinstance(value, ast.Call):
                func = value.func
                called = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
                if called in classes and not _data_class(classes[called]):
                    found.append(Violation("R6", _where(module, stmt), f"module-level instance {label} = {called}(...): only the "
                                                                       "composition root (hirearchy.app) constructs objects"))
                elif called in MUTABLE_FACTORIES and not value.args and not value.keywords:
                    found.append(Violation("R6", _where(module, stmt), f"module-level mutable state {label} = {called}(): move it "
                                                                       "to a process resource of hirearchy.app"))
            elif (isinstance(value, ast.Dict) and not value.keys) or (isinstance(value, (ast.List, ast.Set)) and not value.elts):
                found.append(Violation("R6", _where(module, stmt), f"module-level mutable state {label} = empty container: move it "
                                                                   "to a process resource of hirearchy.app"))
    return found


# ------------------------------------------------------------------------------------------------------------------- R9


def _strings(node: ast.AST) -> Iterator[str]:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            yield sub.value
        elif isinstance(sub, ast.JoinedStr):  # f-strings: the literal pieces
            for part in sub.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    yield part.value


def _names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def matches_fragment(text: str, fragment: str) -> bool:
    """``fragment`` as a whole path segment of ``text``; fragments containing "/", "." or "-" also as a substring."""
    segments = re.split(r"[/\\]", text)
    if fragment in segments:
        return True
    return any(c in fragment for c in "/.-") and fragment in text


def _call_name(call: ast.Call) -> str:
    func = call.func
    return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""


def _is_write(call: ast.Call) -> str | None:
    """The operation name when ``call`` writes (``open`` only with a writing mode), else None."""
    name = _call_name(call)
    if name not in WRITE_CALLS:
        return None
    if name == "open":
        modes = [a.value for a in call.args[1:2] if isinstance(a, ast.Constant)]
        modes += [k.value.value for k in call.keywords if k.arg == "mode" and isinstance(k.value, ast.Constant)]
        return name if any(isinstance(m, str) and set(m) & set("wax+") for m in modes) else None
    return name


def _own_nodes(scope: ast.AST) -> Iterator[ast.AST]:
    """The nodes of a scope without those of nested functions (they are scopes of their own)."""
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            stack.extend(ast.iter_child_nodes(node))


def _scopes(module: ast.Module) -> Iterator[ast.AST]:
    yield module
    for node in ast.walk(module):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _writes_in(scope: ast.AST) -> Iterator[tuple[ast.Call, str, set[str]]]:
    """(call, operation, string constants it mentions) for every write call of the scope, following simple assignments:
    ``p = root / "ORG.md"; p.write_text(..)`` mentions "ORG.md"."""
    nodes = list(_own_nodes(scope))
    assigned: dict[str, set[str]] = {}
    for node in sorted((n for n in nodes if isinstance(n, ast.Assign)), key=lambda n: n.lineno):
        texts = set(_strings(node.value))
        for var in _names(node.value):
            texts |= assigned.get(var, set())
        for target in node.targets:
            if isinstance(target, ast.Name):
                assigned.setdefault(target.id, set()).update(texts)
    for node in nodes:
        if isinstance(node, ast.Call) and (op := _is_write(node)):
            texts = set(_strings(node))
            for var in _names(node):
                texts |= assigned.get(var, set())
            yield node, op, texts


def single_writer(tree: Tree, owners: Iterable[ownership.Owned] = ownership.OWNERS,
                  creators: Mapping[str, tuple[tuple[str, ...], frozenset[str]]] = ownership.CREATORS,
                  not_blamed: Iterable[str] = ownership.NOT_BLAMED) -> list[Violation]:
    """R9: a package other than the owner mentions an owned path fragment inside a write call."""
    found = []
    skip = set(not_blamed)
    for module in tree.modules():
        if module.package in skip or module.package == "":
            continue
        if module.name.split(".")[-1] == "testing":
            continue  # fakes are not production writers
        seen: set[int] = set()
        for scope in _scopes(module.ast):
            for call, op, texts in _writes_in(scope):
                if id(call) in seen:
                    continue
                for owned in owners:
                    if owned.owner == module.package:
                        continue
                    hit = next((f for f in owned.fragments if any(matches_fragment(t, f) for t in texts)), None)
                    if hit is None:
                        continue
                    allowed_fragments, allowed_ops = creators.get(module.package, ((), frozenset()))
                    empty_file = op == "write_text" and bool(call.args) and isinstance(call.args[0], ast.Constant) \
                        and call.args[0].value == ""
                    if hit in allowed_fragments and op in allowed_ops and (op != "write_text" or empty_file):
                        continue  # creator exception: directories and empty files, never content
                    seen.add(id(call))
                    found.append(Violation("R9", _where(module, call),
                                           f"{module.package} writes {owned.path!r} ({op}), whose only writer is {owned.owner}"))
                    break
    return found


LEDGER_CALLS = frozenset({"ledger", "save_ledger"})


def ledger_names(tree: Tree, ledgers: Mapping[str, str] = ownership.LEDGERS,
                 not_blamed: Iterable[str] = ownership.NOT_BLAMED) -> list[Violation]:
    """R9: a ledger name literal passed to a ledger call appears only in the package that owns the ledger."""
    found = []
    for module in tree.modules():
        if module.package in set(not_blamed) or module.package == "":
            continue
        for node in ast.walk(module.ast):
            if not (isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant)):
                continue
            literal = node.args[0].value
            func = node.func
            receiver = ""
            if isinstance(func, ast.Attribute):
                receiver = ast.unparse(func.value).lower()
            is_ledger_call = _call_name(node) in LEDGER_CALLS or ("ledger" in receiver and _call_name(node) in ("read", "write"))
            if is_ledger_call and isinstance(literal, str) and literal in ledgers and ledgers[literal] != module.package:
                found.append(Violation("R9", _where(module, node), f"ledger {literal!r} belongs to {ledgers[literal]}, "
                                                                   f"not to {module.package}"))
    return found


# ------------------------------------------------------------------------------------------------------------------ R13

def responsibility_sentences(markdown: str) -> dict[str, str]:
    """{package: one-sentence responsibility} from the package-map table (ARCHITECTURE.md 2.2)."""
    return {row.name: row.responsibility for row in document.package_rows(markdown)}


def responsibilities(markdown: str) -> list[Violation]:
    """R13: the one-sentence responsibility of a package contains no " and "."""
    return [Violation("R13", f"package {name}", f"the responsibility {sentence!r} contains 'and': split the package")
            for name, sentence in responsibility_sentences(markdown).items() if re.search(r"\sand\s", sentence, re.IGNORECASE)]


# ------------------------------------------------------------------------------------------------------------------- R1


def package_contents(tree: Tree, known: Iterable[str] | None = None) -> list[Violation]:
    """2.1: a package directory holds only __init__.py, api.py, testing.py, tests/, _*.py (and its declared data); every package
    directory is one of the packages of the map (``known`` defaults to the 42 of graph.py)."""
    known_names = set(graph.ALL_PACKAGES if known is None else known)
    found = []
    for directory in tree.package_dirs():
        if directory.name not in known_names:
            found.append(Violation("R1", str(directory.name), "not a package of the architecture map (2.2)"))
        data = PACKAGE_DATA.get(directory.name, ())
        for entry in sorted(directory.iterdir()):
            name = entry.name
            if name.startswith("_") or name in ("api.py", "testing.py", "tests", "py.typed"):
                continue
            if any(re.fullmatch(p.replace(".", r"\.").replace("*", ".*"), name) for p in data):
                continue
            found.append(Violation("R1", f"{directory.name}/{name}", "only __init__.py, api.py, testing.py, tests/ and _*.py "
                                                                      "are allowed in a package (public code lives in api.py)"))
        if not (directory / "api.py").is_file() and directory.name != "app":
            found.append(Violation("R1", directory.name, "a package without api.py (the only public surface)"))
    return found


def init_reexports(tree: Tree, compat: Mapping[str, Iterable[str]] | None = None) -> list[Violation]:
    """R1: ``__init__.__all__ == api.__all__`` and nothing else public, apart from the names of the compatibility surface
    (``compat`` = ``compat_surface.PACKAGE_EXPORTS``: package -> the extra names its ``__init__`` exports). Imports the packages."""
    compat = compat or {}
    found = []
    base = tree.directory.parent
    added = str(base) not in sys.path
    if added:
        sys.path.insert(0, str(base))
    try:
        for directory in tree.package_dirs():
            if not (directory / "api.py").is_file():
                continue
            package = importlib.import_module(f"{tree.name}.{directory.name}")
            api = importlib.import_module(f"{tree.name}.{directory.name}.api")
            api_all = getattr(api, "__all__", None)
            if api_all is None:
                found.append(Violation("R1", f"{directory.name}.api", "api.py defines no __all__"))
                continue
            extra = set(compat.get(directory.name, ()))
            declared = set(getattr(package, "__all__", ()))
            if declared != set(api_all) | extra:
                found.append(Violation("R1", f"{directory.name}.__init__", f"__all__ differs from api.__all__: "
                                                                          f"{sorted(declared ^ (set(api_all) | extra))}"))
            submodules = {p.stem for p in directory.glob("*.py")} | {p.name for p in directory.iterdir() if p.is_dir()}
            public = {n for n in vars(package) if not n.startswith("_") and n not in submodules}
            if public - declared:
                found.append(Violation("R1", f"{directory.name}.__init__", f"public names that are not in api.__all__: "
                                                                          f"{sorted(public - declared)}"))
    finally:
        if added:
            sys.path.remove(str(base))
    return found


# ------------------------------------------------------------------------------------------------------------------- R8


def protocols_of_api(tree: Tree) -> dict[str, list[str]]:
    """{package: [Protocol names in its api.py]}."""
    out: dict[str, list[str]] = {}
    for directory in tree.package_dirs():
        api = directory / "api.py"
        if api.is_file():
            module = ast.parse(api.read_text(encoding="utf-8"))
            names = [n.name for n in ast.walk(module) if isinstance(n, ast.ClassDef) and _is_protocol(n)]
            if names:
                out[directory.name] = names
    return out


def _implementations(directory: Path) -> tuple[dict[str, int], object]:
    """({protocol name: number of factories}, PURE) read from ``testing.py`` by AST."""
    testing = directory / "testing.py"
    if not testing.is_file():
        return {}, None
    entries: dict[str, int] = {}
    pure: object = None
    for stmt in ast.parse(testing.read_text(encoding="utf-8")).body:
        target = stmt.targets[0] if isinstance(stmt, ast.Assign) else stmt.target if isinstance(stmt, ast.AnnAssign) else None
        if not isinstance(target, ast.Name) or getattr(stmt, "value", None) is None:
            continue
        if target.id == "IMPLEMENTATIONS" and isinstance(stmt.value, ast.Dict):
            for key, value in zip(stmt.value.keys, stmt.value.values):
                name = key.id if isinstance(key, ast.Name) else key.attr if isinstance(key, ast.Attribute) else None
                if name:
                    entries[name] = len(value.elts) if isinstance(value, (ast.List, ast.Tuple)) else 1
        elif target.id == "PURE":
            v = stmt.value
            pure = v.value if isinstance(v, ast.Constant) else {e.id if isinstance(e, ast.Name) else str(getattr(e, "value", ""))
                                                              for e in getattr(v, "elts", [])}
    return entries, pure


def contract_suites(tree: Tree, pending: Mapping[str, str] = contract_debt.PENDING) -> list[Violation]:
    """R8: each Protocol of an api.py has ``tests/test_contract_<snake_name>.py`` (which uses IMPLEMENTATIONS) and an entry in
    ``testing.IMPLEMENTATIONS`` with at least a real and a fake implementation, or is declared pure-logic (``PURE = True`` or
    ``PURE = {"Name", ...}`` in testing.py). Protocols in ``pending`` (``contract_debt.PENDING``) are owed by a later step."""
    found = []
    for package, protocols in protocols_of_api(tree).items():
        directory = tree.directory / package
        entries, pure = _implementations(directory)
        for name in protocols:
            problems = []
            suite = directory / "tests" / f"test_contract_{_snake(name)}.py"
            is_pure = pure is True or (isinstance(pure, set) and name in pure)
            if not suite.is_file():
                problems.append(f"no contract suite {suite.relative_to(tree.directory)}")
            elif "IMPLEMENTATIONS" not in suite.read_text(encoding="utf-8") and not is_pure:
                problems.append(f"{suite.name} does not iterate over testing.IMPLEMENTATIONS")
            if not is_pure and entries.get(name, 0) < 2:
                problems.append("testing.IMPLEMENTATIONS needs at least a real and a fake implementation (or declare the Protocol PURE)")
            key = f"{package}.{name}"
            if key in pending:
                if problems:
                    continue  # owed by a later step
                found.append(Violation("R8", f"{package}.api.{name}", f"its contract suite exists (owed by {pending[key]}): "
                                                                      "remove it from contract_debt.PENDING"))
            else:
                found.extend(Violation("R8", f"{package}.api.{name}", problem) for problem in problems)
    return found


# --------------------------------------------------------------------------------------------------------- dependency graph


def imported_packages(module: Module, root: str) -> set[str]:
    """Top-level packages of ``root`` that ``module`` imports (function-level imports included)."""
    found: set[str] = set()
    base = module.name.split(".") if module.is_package else module.name.split(".")[:-1]
    for node in ast.walk(module.ast):
        targets: list[str] = []
        if isinstance(node, ast.Import):
            targets = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                prefix = base[: len(base) - (node.level - 1)] if node.level > 1 else base
                dotted = ".".join([*prefix, *(node.module.split(".") if node.module else [])])
            else:
                dotted = node.module or ""
            targets = [dotted]
            if dotted == root:  # ``from hirearchy import mail``: the imported names are modules
                targets = [f"{root}.{a.name}" for a in node.names]
        for target in targets:
            parts = target.split(".")
            if parts[0] == root and len(parts) > 1:
                found.add(parts[1])
    return found


def imports_against_graph(tree: Tree, packages: Mapping[str, graph.Package] = graph.PACKAGES) -> list[Violation]:
    """The imports that actually exist between packages are a subset of the edges of 2.2/4.3 (the layers contract proves the
    level order; this proves the finer, per-package list). ``app`` may import everything."""
    found = []
    for module in tree.modules():
        package = module.package
        if package not in packages:
            continue  # app, unknown packages (package_contents reports those)
        allowed = graph.allowed_imports(package) if packages is graph.PACKAGES else \
            frozenset(packages[package].deps) | {package, graph.KERNEL}
        for target in sorted(imported_packages(module, tree.name) - allowed):
            if target in packages:
                found.append(Violation("R4", module.name, f"imports {target}, which {package} may not depend on "
                                                          f"(allowed: {', '.join(sorted(allowed - {package}))})"))
    return found
