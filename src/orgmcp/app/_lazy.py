"""Lazy ports: the mechanism behind ``OrgRuntime`` (ARCHITECTURE.md 6.2).

A runtime does not build its ports when it is opened: ``org.runtime.mailbox`` asks the resolver (the ``Builder``) the first time the
attribute is read and keeps the answer in the instance, so the next read is a plain attribute read. The ports are the annotated fields of
the class, whatever parts it is composed of (``fields_<pkg>.Fields``): a part added later needs no change here.
"""

from __future__ import annotations

import typing
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, Self, TypeVar

T = TypeVar("T")


class PortResolver(Protocol):
    """What a lazy runtime needs of the builder: the organization root and the one object of each port."""

    @property
    def root(self) -> Path: ...

    def get(self, port: type[T]) -> T: ...


_PORTS: dict[type, dict[str, type]] = {}  # per runtime class: field name -> port (read once from the annotations of the parts)


def ports_of(cls: type) -> dict[str, type]:
    """The port of every annotated field of ``cls`` except ``root`` (the one field that is not built by a provider)."""
    ports = _PORTS.get(cls)
    if ports is None:
        ports = _PORTS[cls] = {name: port for name, port in typing.get_type_hints(cls).items() if name != "root"}
    return ports


class LazyPorts:
    """Base of a frozen dataclass declared with ``init=False``: its fields are filled by keyword (``dataclasses.replace`` does that, and
    reads every other field, which resolves it) or resolved on first access through the resolver given at ``lazy``."""

    def __init__(self, resolver: PortResolver | None = None, /, **values: object) -> None:
        state = self.__dict__
        state.update(values)
        if resolver is not None:
            state["_resolver"] = resolver

    @classmethod
    def lazy(cls, resolver: PortResolver) -> Self:
        """The runtime of ``resolver.root`` whose ports are built, by ``resolver``, when they are first read."""
        return cls(resolver, root=resolver.root)

    if not TYPE_CHECKING:  # for mypy the fields are the ones the parts declare; a typo must stay an error

        def __getattr__(self, name: str) -> object:
            # only reached when the instance has no such entry yet (the first read of a port)
            resolver = self.__dict__.get("_resolver")
            port = ports_of(type(self)).get(name)
            if resolver is None or port is None:
                raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")
            value = self.__dict__[name] = resolver.get(port)
            return value
