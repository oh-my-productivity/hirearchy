"""The public surface of ``settings``: ORG.md, its settings block and its rules text.

``OrgSettings`` reads the settings and the rules, ``OrgDocumentStore`` is the raw file (the only way to write it), and
``EventSwitch`` answers whether the event log is on. The pure functions read one value out of a settings mapping.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..kernel import JsonObject
from ._config import (
    DEFAULT_CONFIG,
    DEFAULT_MODEL,
    config_default_model,
    config_message_cap,
    config_number,
    finite_number,
)

__all__ = [
    "DEFAULT_CONFIG",
    "DEFAULT_MODEL",
    "EventSwitch",
    "OrgDocumentStore",
    "OrgSettings",
    "config_default_model",
    "config_message_cap",
    "config_number",
    "finite_number",
]


@runtime_checkable
class OrgSettings(Protocol):
    def config(self) -> JsonObject:
        """The ORG.md frontmatter merged over ``DEFAULT_CONFIG``."""
        ...

    def rules(self) -> str:
        """The ORG.md body, stripped."""
        ...

    def default_model(self) -> str:
        """``default_model`` of the config, else ``DEFAULT_MODEL`` (also for ``null`` or an empty value)."""
        ...

    def number(self, key: str, kind: type[float] | type[int] = float) -> float:
        """A numeric setting as ``kind``; a missing or malformed value (not finite, a bool, a bad string) means the default."""
        ...

    def message_cap(self) -> int:
        """``max_message_chars``; a malformed value or one that is not positive means the default."""
        ...


@runtime_checkable
class OrgDocumentStore(Protocol):
    def exists(self) -> bool:
        """ORG.md exists (as a file)."""
        ...

    def read_raw(self) -> str:
        """The file exactly as written."""
        ...

    def write_raw(self, text: str) -> None:
        """Atomically replace the file."""
        ...


@runtime_checkable
class EventSwitch(Protocol):
    def enabled(self) -> bool:
        """False when ORG.md is missing or says ``events: false``; ORG.md is read again only when it changes."""
        ...
