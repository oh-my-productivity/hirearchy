"""Patch-point adapters: the module attributes that tests replace (``core.utcnow``, ``core.atomic_write``, ``core._PARSED_MAX``,
``core.split_frontmatter``) stay in force while the code that reads them lives elsewhere (ARCHITECTURE.md 6.4, rule 4).

Every adapter is deleted by the E1 step that converts its last test; the module by E2.
"""

from __future__ import annotations

import importlib
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import cast

from ..kernel import AtomicWriter, JsonObject, Message
from ..kernel._system import SystemClock
from ._resources import CachingMessageParser

ENABLED = True  # False: open_runtime wires the plain system adapters (what the module will do once the tests are converted)


def _core() -> ModuleType:
    """``orgmcp.core``, looked up at call time (it imports the app package, so the app cannot import it at load time)."""
    return sys.modules.get("orgmcp.core") or importlib.import_module("orgmcp.core")


def utcnow() -> datetime:
    """``orgmcp.core.utcnow()``, looked up at call time (patch point ``core.utcnow``)."""
    return cast(datetime, _core().utcnow())


def atomic_write(path: Path, text: str) -> None:
    """``orgmcp.core.atomic_write(path, text)``, looked up at call time (patch point ``core.atomic_write``)."""
    _core().atomic_write(path, text)


class PatchPointClock(SystemClock):
    """The system clock whose ``now`` is whatever ``orgmcp.core.utcnow`` is at the time of the call."""

    def now(self) -> datetime:
        return utcnow()


class PatchPointAtomicWriter(AtomicWriter):
    def write(self, path: Path, text: str) -> None:
        atomic_write(path, text)


class PatchPointMessageParser(CachingMessageParser):
    """The parse cache with its limit and its splitter read from ``orgmcp.core`` at call time.

    ``core._PARSED`` is this parser's cache (the same dict); ``core._PARSED_MAX`` and ``core.split_frontmatter`` may be replaced.
    """

    @property
    def max_entries(self) -> int:
        return cast(int, _core()._PARSED_MAX)

    def _split_text(self, text: str) -> tuple[JsonObject, str]:
        return cast("tuple[JsonObject, str]", _core().split_frontmatter(text))


def install_message_load(parser: CachingMessageParser) -> None:
    """Attach the legacy classmethod ``Message.load`` (served by ``parser``) to the kernel's ``Message``.

    The kernel's ``Message`` is pure data; reading a file (and caching the parse) belongs to the mail package, which takes
    ``Message.load`` over in step A-mail. Until then every caller of ``Message.load`` gets the process parser.
    """

    def load(cls: type[Message], path: Path) -> Message:
        return parser.parse_as(cls, path)

    Message.load = classmethod(load)  # type: ignore[attr-defined]

