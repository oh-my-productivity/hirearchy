"""RED skeleton (step A-skill): providers of the ``skill`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from pathlib import Path

from ._builder import Builder


def package_dir() -> Path:
    raise NotImplementedError


def register(b: Builder) -> None:
    """Nothing is provided yet."""
