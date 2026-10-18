"""The builder: lazy singletons per runtime, resolved by port (ARCHITECTURE.md 6.2). RED skeleton (M2)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")


class BuilderError(Exception):
    """A wiring mistake: caught by the tests of the wiring, never by production code."""


class NotProvided(BuilderError, LookupError):
    """``get`` of a port that no ``wire_*`` module provides and no override replaces."""


class DuplicateProvider(BuilderError):
    """Two ``wire_*`` modules claim the same port."""


class DependencyCycle(BuilderError):
    """A provider asked, directly or through others, for the port it is building."""


class Builder:
    """Providers register a factory per port; ``get`` builds each port once and hands out the same object afterwards."""

    def __init__(self, root: Path, overrides: Mapping[type, object] | None = None) -> None:
        raise NotImplementedError("red: M2")

    @property
    def root(self) -> Path:
        """The organization directory the runtime is built for."""
        raise NotImplementedError("red: M2")

    def provide(self, port: type[T], factory: Callable[[Builder], T]) -> None:
        """Register how ``port`` is built; the factory runs on the first ``get``, not now."""
        raise NotImplementedError("red: M2")

    def get(self, port: type[T]) -> T:
        """The one object of ``port`` of this builder (an override wins over the provider)."""
        raise NotImplementedError("red: M2")
