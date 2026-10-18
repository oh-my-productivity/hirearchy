"""RED skeleton (M0)."""

from __future__ import annotations

from pathlib import Path

LEGACY_EXPORTS: dict[str, dict[str, str]] = {}
PERMANENT_MODULES: set[str] = set()


def check(src: Path) -> list[str]:
    raise NotImplementedError


def exported_names_by_package(src: Path | None = None) -> dict[str, set[str]]:
    raise NotImplementedError
