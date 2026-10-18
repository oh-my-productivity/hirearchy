"""RED skeleton (M0): the structural checkers; every function raises NotImplementedError until the GREEN commit."""

from __future__ import annotations

import ast
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from . import graph, ownership


@dataclass(frozen=True)
class Violation:
    rule: str
    where: str
    message: str


@dataclass(frozen=True)
class Module:
    name: str
    package: str
    path: Path
    ast: ast.Module
    is_package: bool


class Tree:
    def __init__(self, directory: Path, name: str | None = None) -> None:
        self.directory = directory
        self.name = name or directory.name

    def package_dirs(self) -> list[Path]:
        raise NotImplementedError

    def package_names(self) -> list[str]:
        raise NotImplementedError

    def modules(self, *, tests: bool = False, packages_only: bool = True) -> Iterator[Module]:
        raise NotImplementedError


def protocol_widths(tree: Tree, limit: int = 8) -> list[Violation]:
    raise NotImplementedError


def module_singletons(tree: Tree, skip: Iterable[str] = ("app",)) -> list[Violation]:
    raise NotImplementedError


def single_writer(tree: Tree) -> list[Violation]:
    raise NotImplementedError


def ledger_names(tree: Tree) -> list[Violation]:
    raise NotImplementedError


def responsibility_sentences(markdown: str) -> dict[str, str]:
    raise NotImplementedError


def responsibilities(markdown: str) -> list[Violation]:
    raise NotImplementedError


def package_contents(tree: Tree, known: Iterable[str] | None = None) -> list[Violation]:
    raise NotImplementedError


def init_reexports(tree: Tree, legacy: Mapping[str, Iterable[str]] | None = None) -> list[Violation]:
    raise NotImplementedError


def contract_suites(tree: Tree) -> list[Violation]:
    raise NotImplementedError


def imports_against_graph(tree: Tree, packages: Mapping[str, graph.Package] = graph.PACKAGES) -> list[Violation]:
    raise NotImplementedError


_ = ownership
