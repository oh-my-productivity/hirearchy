"""The composition root's public entry points (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from types import MappingProxyType

from ..mail._index import StampCachedMetaReader
from ..mail._parser import CachingMessageParser
from ._builder import Builder
from ._lazy import ports_of
from ._resources import ProcessResources
from .runtime import OrgRuntime

_process: ProcessResources | None = None  # the one set of process resources (app is the only place for such a global)
_registrars: list[Callable[[Builder], None]] | None = None
_providers: Mapping[type, Callable[[Builder], object]] | None = None  # the factory of every port, collected once for the process
_overrides: Mapping[type, object] = MappingProxyType({})  # the ports replaced for every runtime opened now (``overriding``); empty in production


def new_process_resources() -> ProcessResources:
    """A fresh set of process resources: the parse and front-matter caches, the event pool, process label, trace scope and event sinks."""
    return ProcessResources(CachingMessageParser(), StampCachedMetaReader())


def process_resources() -> ProcessResources:
    """The resources of this process (created on the first call): every runtime and every ``Org`` in it shares them."""
    global _process
    if _process is None:
        _process = new_process_resources()
    return _process


def wire_modules() -> list[str]:
    """Dotted names of the ``hirearchy.app.wire_*`` modules, sorted: each declares the providers of one package."""
    package = __package__ or "hirearchy.app"
    here = importlib.import_module(package)
    return sorted(f"{package}.{m.name}" for m in pkgutil.iter_modules(here.__path__) if m.name.startswith("wire_"))


def registrars() -> list[Callable[[Builder], None]]:
    """The ``register`` function of every ``wire_*`` module, in the order of ``wire_modules``."""
    global _registrars
    if _registrars is None:
        _registrars = [importlib.import_module(name).register for name in wire_modules()]
    return _registrars


def runtime_ports() -> dict[str, type]:
    """The port of every field of ``OrgRuntime`` except ``root`` (the one field that is not built by a provider)."""
    return ports_of(OrgRuntime)


def providers() -> Mapping[type, Callable[[Builder], object]]:
    """The factory of every port: the process resources and what each ``wire_*`` module registers, collected on the first call.

    The factories only name the ports they need (they read nothing of the runtime that uses them), so every builder starts from this one table."""
    global _providers
    if _providers is None:
        collected = Builder(Path("."))
        collected.provide(ProcessResources, lambda _: process_resources())
        for register in registrars():
            register(collected)
        _providers = collected.providers
    return _providers


@contextmanager
def overriding(overrides: Mapping[type, object]) -> Iterator[None]:
    """For the length of the block, every runtime opened in this process starts from ``overrides`` (port -> object).

    The explicit ``overrides`` of ``open_runtime`` win over these, and an inner block over an outer one. It is the one seam for code that opens its
    own runtime (a command of the CLI, a tool of the MCP server, the scheduler, ``Org(root)``): a test gives it a fake ``Clock`` or ``TokenSource``
    here. Only runtimes opened inside the block are affected (a port is chosen when the runtime is opened). Production never calls this."""
    global _overrides
    saved = _overrides
    _overrides = MappingProxyType({**saved, **overrides})
    try:
        yield
    finally:
        _overrides = saved


def overrides() -> Mapping[type, object]:
    """The ports ``overriding`` is replacing right now (read-only; empty outside every block)."""
    return _overrides


def open_runtime(root: Path, overrides: Mapping[type, object] | None = None) -> OrgRuntime:
    """The runtime of the organization at ``root`` (resolved by the caller). Constructors do no I/O; ``overrides`` replace ports.

    Nothing is built here: each port is built, once, when the runtime is first asked for it (``org.runtime.mailbox``)."""
    return OrgRuntime.lazy(Builder(root, {**_overrides, **overrides} if overrides else (_overrides or None), providers()))

