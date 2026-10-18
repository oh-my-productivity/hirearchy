"""Patch-point adapters: the module attributes that tests replace (``core.utcnow``, ``core.atomic_write``, ``core.secrets``) stay in force
while the code that reads them lives elsewhere (ARCHITECTURE.md 6.4, rule 4); and the legacy classmethod ``Message.load``.

Every adapter is deleted by the E1 step that converts its last test; the module by E2. (The parse cache has no adapter any more: the
tests that replaced ``core.split_frontmatter`` / ``core._PARSED_MAX`` inject a ``CachingMessageParser`` through ``open_runtime`` since A-mail.)
"""

from __future__ import annotations

import importlib
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import cast

from ..kernel import AtomicWriter, Message
from ..kernel._system import SystemClock
from ..mail._parser import CachingMessageParser

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


class CoreSecrets:
    """The ``secrets`` module of ``orgmcp.core`` (patch point ``core.secrets``: the golden suite replaces it with a counter so message
    ids are stable); ``token_hex`` is looked up at call time."""

    @staticmethod
    def token_hex(nbytes: int | None = None) -> str:
        return cast(str, _core().secrets.token_hex(nbytes))


secrets = CoreSecrets()  # what the mixins' `secrets.token_hex(...)` resolves to


class PatchPointClock(SystemClock):
    """The system clock whose ``now`` is whatever ``orgmcp.core.utcnow`` is at the time of the call."""

    def now(self) -> datetime:
        return utcnow()


class PatchPointAtomicWriter(AtomicWriter):
    def write(self, path: Path, text: str) -> None:
        atomic_write(path, text)


def install_message_load(parser: CachingMessageParser) -> None:
    """Attach the legacy classmethod ``Message.load`` (served by ``parser``) to the kernel's ``Message``.

    The kernel's ``Message`` is pure data; reading a file (and caching the parse) belongs to the mail package
    (``MessageParser``). The legacy callers that still say ``Message.load(path)`` (``dashboard_data``, the facade's trace lookups, the
    tests) get the process parser until E1 converts them.
    """

    def load(cls: type[Message], path: Path) -> Message:
        return parser.parse_as(cls, path)

    Message.load = classmethod(load)  # type: ignore[attr-defined]

