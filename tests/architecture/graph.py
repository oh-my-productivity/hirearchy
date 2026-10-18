"""RED skeleton (M0): replaced in the GREEN commit."""

from __future__ import annotations

from dataclasses import dataclass

KERNEL = "kernel"
APP = "app"


@dataclass(frozen=True)
class Package:
    name: str
    kind: str
    deps: tuple[str, ...]


PACKAGES: dict[str, Package] = {}
FEATURES: tuple[str, ...] = ()
ENTRY_POINTS: tuple[str, ...] = ()
ALL_PACKAGES: tuple[str, ...] = ()


def level(name: str) -> int:
    raise NotImplementedError


def feature_levels() -> dict[int, tuple[str, ...]]:
    raise NotImplementedError


def edges() -> set[tuple[str, str]]:
    raise NotImplementedError


def allowed_imports(name: str) -> frozenset[str]:
    raise NotImplementedError
