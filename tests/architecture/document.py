"""RED skeleton (M0): parsers of ARCHITECTURE.md."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PackageRow:
    name: str
    kind: str
    responsibility: str
    deps: tuple[str, ...]


def package_rows(markdown: str) -> list[PackageRow]:
    raise NotImplementedError


def edge_rows(markdown: str) -> set[tuple[str, str]]:
    raise NotImplementedError


def level_rows(markdown: str) -> dict[str, tuple[str, ...]]:
    raise NotImplementedError


def ownership_rows(markdown: str) -> list[tuple[str, str]]:
    raise NotImplementedError


def ledger_registry(markdown: str) -> dict[str, str]:
    raise NotImplementedError


def mapping_symbols(markdown: str) -> dict[str, set[str]]:
    raise NotImplementedError
