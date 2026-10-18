"""Patch-point adapters: the module attributes that tests replace (``core.utcnow``, ``core.atomic_write``, ``core._PARSED_MAX``,
``core.split_frontmatter``) stay in force while the code that reads them lives elsewhere (ARCHITECTURE.md 6.4, rule 4).
RED skeleton (M2). Every adapter is deleted by the E1 step that converts its last test; the module by E2."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..kernel import AtomicWriter, Clock
from ._resources import CachingMessageParser

ENABLED = True  # False: open_runtime wires the plain system adapters (what the module will do once the tests are converted)


def utcnow() -> datetime:
    """``orgmcp.core.utcnow()``, looked up at call time."""
    raise NotImplementedError("red: M2")


def atomic_write(path: Path, text: str) -> None:
    """``orgmcp.core.atomic_write(path, text)``, looked up at call time."""
    raise NotImplementedError("red: M2")


class PatchPointClock(Clock):
    def now(self) -> datetime:
        raise NotImplementedError("red: M2")

    def time(self) -> float:
        raise NotImplementedError("red: M2")

    def monotonic(self) -> float:
        raise NotImplementedError("red: M2")

    def sleep(self, seconds: float) -> None:
        raise NotImplementedError("red: M2")


class PatchPointAtomicWriter(AtomicWriter):
    def write(self, path: Path, text: str) -> None:
        raise NotImplementedError("red: M2")


class PatchPointMessageParser(CachingMessageParser):
    """The parse cache with the limit and the splitter read from ``orgmcp.core`` at call time."""


def install_message_load(parser: CachingMessageParser) -> None:
    """Attach the legacy classmethod ``Message.load`` (served by ``parser``) to the kernel's ``Message``."""
    raise NotImplementedError("red: M2")

