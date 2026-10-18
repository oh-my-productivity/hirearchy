"""The builder: lazy singletons per runtime, resolved by port (ARCHITECTURE.md 6.2)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TypeVar, cast

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
        self._root = root
        self._objects: dict[type, object] = dict(overrides or {})  # an override is an object that is already built
        self._factories: dict[type, Callable[[Builder], object]] = {}
        self._building: list[type] = []

    @property
    def root(self) -> Path:
        """The organization directory the runtime is built for."""
        return self._root

    def provide(self, port: type[T], factory: Callable[[Builder], T]) -> None:
        """Register how ``port`` is built; the factory runs on the first ``get``, not now."""
        if port in self._factories:
            raise DuplicateProvider(f"{port.__name__} is provided twice")
        self._factories[port] = factory

    def get(self, port: type[T]) -> T:
        """The one object of ``port`` of this builder (an override wins over the provider)."""
        if port in self._objects:
            return cast(T, self._objects[port])
        if port in self._building:
            path = " -> ".join(p.__name__ for p in (*self._building[self._building.index(port) :], port))
            raise DependencyCycle(f"dependency cycle: {path}")
        factory = self._factories.get(port)
        if factory is None:
            raise NotProvided(f"no provider for {port.__name__}")
        self._building.append(port)
        try:
            built = factory(self)
        finally:
            self._building.pop()
        self._objects[port] = built
        return cast(T, built)
