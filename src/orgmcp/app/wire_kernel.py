"""Providers of the kernel's ports (ARCHITECTURE.md 6.1). RED skeleton (M2)."""

from __future__ import annotations

from ._builder import Builder


def register(b: Builder) -> None:
    raise NotImplementedError("red: M2")
