"""RED skeleton (M0)."""

from __future__ import annotations

from pathlib import Path

SECTIONS: dict[str, tuple[str, ...]] = {}


def missing_from_mapping(src: Path, markdown: str) -> list[str]:
    raise NotImplementedError
