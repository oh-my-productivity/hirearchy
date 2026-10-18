"""RED skeleton (M0): replaced in the GREEN commit."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Owned:
    path: str
    owner: str
    fragments: tuple[str, ...]


OWNERS: tuple[Owned, ...] = ()
CREATORS: dict[str, tuple[tuple[str, ...], frozenset[str]]] = {}
NOT_BLAMED: frozenset[str] = frozenset()
LEDGERS: dict[str, str] = {}
