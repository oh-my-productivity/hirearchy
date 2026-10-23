"""The public surface of ``settings``: ORG.md, its settings block and its rules text.

``OrgSettings`` reads the settings and the rules, ``OrgDocumentStore`` is the raw file (the only way to write it), and
``EventSwitch`` answers whether the event log is on. The pure functions read one value out of a settings mapping; the ``*_floor_problem``
ones are the org-agent floor (the allowed models and the effort levels, docs/design/org-agent-model-floor.md).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..kernel import JsonObject
from ._config import (
    DEFAULT_CONFIG,
    DEFAULT_EFFORT,
    DEFAULT_MODEL,
    config_default_model,
    config_message_cap,
    config_number,
    finite_number,
)
from ._floor import (
    DEFAULT_ALLOWED_MODELS,
    EFFORT_LEVELS,
    config_allowed_models,
    config_effort,
    config_floor_problem,
    effort_floor_problem,
    model_floor_problem,
)

__all__ = [
    "DEFAULT_ALLOWED_MODELS",
    "DEFAULT_CONFIG",
    "DEFAULT_EFFORT",
    "DEFAULT_MODEL",
    "EFFORT_LEVELS",
    "EventSwitch",
    "OrgDocumentStore",
    "OrgSettings",
    "config_allowed_models",
    "config_default_model",
    "config_effort",
    "config_floor_problem",
    "config_message_cap",
    "config_number",
    "effort_floor_problem",
    "finite_number",
    "model_floor_problem",
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
