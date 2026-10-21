"""The builder: lazy singletons per runtime, resolved by port (ARCHITECTURE.md 6.2)."""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import TypeVar, cast

from ._lazy import PortResolver

T = TypeVar("T")


class BuilderError(Exception):
    """A wiring mistake: caught by the tests of the wiring, never by production code."""


class NotProvided(BuilderError, LookupError):
    """``get`` of a port that no ``wire_*`` module provides and no override replaces."""


class DuplicateProvider(BuilderError):
    """Two ``wire_*`` modules claim the same port."""


class DependencyCycle(BuilderError):
    """A provider asked, directly or through others, for the port it is building."""


class Builder(PortResolver):
    """Providers register a factory per port; ``get`` builds each port once and hands out the same object afterwards.

    A factory is stateless (it only names the ports it needs), so the table of the whole process is collected once and handed to every
    builder as ``providers``: opening a runtime registers nothing. ``provide`` adds to the builder's own table."""

    def __init__(
        self,
        root: Path,
        overrides: Mapping[type, object] | None = None,
        providers: Mapping[type, Callable[[Builder], object]] | None = None,
    ) -> None:
        self._root = root
        self._objects: dict[type, object] = dict(overrides or {})  # an override is an object that is already built
        self._shared: Mapping[type, Callable[[Builder], object]] = providers if providers is not None else {}
        self._factories: dict[type, Callable[[Builder], object]] = {}
        self._building: list[type] = []
        self._lock = threading.RLock()  # runtimes are read from several threads (mcp tools, the dashboard): a port is built once

    @property
    def root(self) -> Path:
        """The organization directory the runtime is built for."""
        return self._root

    @property
    def providers(self) -> Mapping[type, Callable[[Builder], object]]:
        """Every factory registered here and in the shared table, read-only: what another builder can start from."""
        return MappingProxyType({**self._shared, **self._factories})

    def provide(self, port: type[T], factory: Callable[[Builder], T]) -> None:
        """Register how ``port`` is built; the factory runs on the first ``get``, not now."""
        if port in self._factories or port in self._shared:
            raise DuplicateProvider(f"{port.__name__} is provided twice")
        self._factories[port] = factory

    def get(self, port: type[T]) -> T:
        """The one object of ``port`` of this builder (an override wins over the provider)."""
        built = self._objects.get(port)
        if built is not None:
            return cast(T, built)
        with self._lock:
            return self._build(port)

    def _build(self, port: type[T]) -> T:
        if port in self._objects:  # built by another thread while this one waited for the lock
            return cast(T, self._objects[port])
        if port in self._building:
            path = " -> ".join(p.__name__ for p in (*self._building[self._building.index(port) :], port))
            raise DependencyCycle(f"dependency cycle: {path}")
        factory = self._factories.get(port) or self._shared.get(port)
        if factory is None:
            raise NotProvided(f"no provider for {port.__name__}")
        self._building.append(port)
        try:
            built = factory(self)
        finally:
            self._building.pop()
        self._objects[port] = built
        return cast(T, built)
