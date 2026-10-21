"""Generates the import-linter contracts of the architecture (ARCHITECTURE.md 8.2) from ``graph.py`` and the packages on disk.

    uv run python -m tests.architecture.gen_importlinter        # prints the config
    uv run python -m tests.architecture.lint                    # writes .importlinter (git-ignored) and runs lint-imports

Why generated: import-linter wildcards must replace a whole module name (``hirearchy.*._*`` is not valid), and a layer whose package does
not exist yet would fail the contract; so the file lists exactly the packages that exist (the others are simply left out) and
one ``private-modules-<pkg>`` contract per package that has ``_*`` modules. Nothing here is edited by a feature step: creating
``src/hirearchy/<pkg>/`` is enough for its contracts to appear.

Contracts (rule in parentheses):

* ``layers`` (R4, R5): app/core -> entry points -> features by level (L11..L1) -> kernel. ``|`` = independent siblings.
* ``private-modules-<pkg>`` (R2): only the package itself (its own tests included) and ``hirearchy.app`` import its ``_*`` modules.
* ``kernel-independent`` (R3): the kernel imports no other module of the root package.
* ``no-facade-import`` (R5): no package imports ``hirearchy.core`` or ``hirearchy.app``.
* ``no-testing-in-production``: ``<pkg>.testing`` is imported only by tests and by other ``testing`` modules.
* ``textual-only-in-dashboard`` / ``mcp-only-in-mcp-server`` / ``yaml-only-where-needed``: frameworks stay at the edge.

The hand-written contracts (what the generator does not derive from the package map: ``hirearchy.core`` does not import the entry points)
are in ``[tool.importlinter]`` of pyproject.toml; ``lint`` runs both.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Mapping

from . import graph
from .checks import Tree

GRAPH: Mapping[str, graph.Package] = graph.PACKAGES
SHIMS = ("app", "core")  # the top layer: the composition root and the permanent facade module over it (a flat module counts)
FRAMEWORKS = (
    ("textual-only-in-dashboard", "Textual is used only by the dashboard entry point", ("dashboard",), ("textual",)),
    ("mcp-only-in-mcp-server", "The MCP SDK is used only by the MCP server entry point", ("mcp_server",), ("mcp", "anyio")),
    ("yaml-only-where-needed", "PyYAML is used only by the kernel (frontmatter) and by blueprint (YAML blueprints)",
     ("kernel", "blueprint"), ("yaml",)),
)


def _block(identifier: str, name: str, kind: str, **fields: list[str] | str) -> str:
    lines = [f"[importlinter:contract:{identifier}]", f"name = {name}", f"type = {kind}"]
    for key, value in fields.items():
        if isinstance(value, list):
            lines.append(f"{key} =")
            lines.extend(f"    {item}" for item in value)
        else:
            lines.append(f"{key} = {value}")
    return "\n".join(lines) + "\n"


def _top_level_modules(tree: Tree) -> list[str]:
    names = {p.stem for p in tree.directory.glob("*.py")} | set(tree.package_names())
    return sorted(names - {"__init__", "__main__"})


def _private_modules(tree: Tree, package: str) -> list[str]:
    directory = tree.directory / package
    names = {p.stem for p in directory.glob("_*.py")} | {p.name for p in directory.iterdir() if p.is_dir() and p.name.startswith("_")}
    return sorted(names - {"__init__", "__pycache__"})


def _imported_externals(tree: Tree, wanted: tuple[str, ...]) -> set[str]:
    """Which of the external top-level packages ``wanted`` are imported anywhere in the tree (flat modules included): import-linter
    fails on a forbidden external module it has never seen."""
    found = set()
    for path in tree.directory.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] if isinstance(node, ast.ImportFrom) and not node.level else []
            found |= {n.split(".")[0] for n in names} & set(wanted)
    return found


def layer_lines(tree: Tree, packages: Mapping[str, graph.Package]) -> list[str]:
    """Top to bottom, only what exists: ``root.app : root.core``, the entry points, one line per feature level, the kernel."""
    root, existing, modules = tree.name, set(tree.package_names()), set(_top_level_modules(tree))
    lines = []
    shims = [f"{root}.{n}" for n in SHIMS if n in modules]
    if shims:
        lines.append(" : ".join(shims))
    entries = sorted(n for n, p in packages.items() if p.kind == "entry" and n in existing)
    if entries:
        lines.append(" | ".join(f"{root}.{n}" for n in entries))
    by_level: dict[int, list[str]] = {}
    for name, package in packages.items():
        if package.kind == "feature" and name in existing:
            by_level.setdefault(_level(name, packages), []).append(name)
    for lvl in sorted(by_level, reverse=True):
        lines.append(" | ".join(f"{root}.{n}" for n in sorted(by_level[lvl])))
    if graph.KERNEL in existing:
        lines.append(f"{root}.{graph.KERNEL}")
    return lines


def _level(name: str, packages: Mapping[str, graph.Package]) -> int:
    deps = [d for d in packages[name].deps if d != graph.KERNEL and d in packages]
    return 1 + max((_level(d, packages) for d in deps), default=0)


def generate(tree: Tree, packages: Mapping[str, graph.Package] = GRAPH) -> str | None:
    """The import-linter config for the packages of ``tree`` that are in ``packages``; None when no contract applies."""
    root, existing, modules = tree.name, set(tree.package_names()), set(_top_level_modules(tree))
    contracts: list[str] = []

    layers = layer_lines(tree, packages)
    if len(layers) >= 2:
        contracts.append(_block("layers", "Layers: app -> entry points -> features (by level) -> kernel", "layers", layers=layers))

    for package in sorted(existing):
        private = _private_modules(tree, package)
        if private:
            allowed = [f"{root}.{package}"] + ([f"{root}.app"] if "app" in existing and package != "app" else [])
            contracts.append(_block(f"private-modules-{package}",
                                    f"Only {root}.{package} (and {root}.app) import the private modules of {root}.{package}",
                                    "protected", protected_modules=[f"{root}.{package}.{m}" for m in private], allowed_importers=allowed))

    if graph.KERNEL in existing and graph.KERNEL in packages:
        others = [f"{root}.{m}" for m in _top_level_modules(tree) if m != graph.KERNEL]
        if others:
            contracts.append(_block("kernel-independent", f"The kernel imports no other module of {root}", "forbidden",
                                    source_modules=[f"{root}.{graph.KERNEL}"], forbidden_modules=others, allow_indirect_imports="True"))

    sources = [f"{root}.{n}" for n in sorted(packages) if n in existing]
    facades = [f"{root}.{n}" for n in SHIMS if n in modules]
    if sources and facades:
        contracts.append(_block("no-facade-import", "Features and entry points never import the Org facade", "forbidden",
                                source_modules=sources, forbidden_modules=facades, allow_indirect_imports="True"))

    testing = [f"{root}.{n}.testing" for n in sorted(existing) if (tree.directory / n / "testing.py").is_file()]
    if testing:
        contracts.append(_block("no-testing-in-production", "Production code never imports a testing module", "protected",
                                protected_modules=testing, allowed_importers=[f"{root}.*.tests", f"{root}.*.testing"]))

    for identifier, name, allowed_packages, forbidden in FRAMEWORKS:
        sources = [f"{root}.{n}" for n in sorted(packages) if n in existing and n not in allowed_packages]
        used = [m for m in forbidden if m in _imported_externals(tree, forbidden)]
        if sources and used:
            contracts.append(_block(identifier, name, "forbidden", source_modules=sources, forbidden_modules=used,
                                    allow_indirect_imports="True"))

    if not contracts:
        return None
    header = f"# GENERATED by tests/architecture/gen_importlinter.py -- do not edit (git-ignored).\n[importlinter]\nroot_package = {root}\n" \
             "include_external_packages = True\n"
    return header + "\n" + "\n".join(contracts)


def main(argv: list[str]) -> int:
    from .paths import SRC

    text = generate(Tree(SRC))
    print(text if text is not None else "# no contract applies yet: no package of the architecture map exists")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

