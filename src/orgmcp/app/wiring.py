"""The composition root's public entry points (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import get_type_hints

from ..mail._index import StampCachedMetaReader
from ..mail._parser import CachingMessageParser
from ._builder import Builder
from ._resources import ProcessResources
from .runtime import OrgRuntime

_process: ProcessResources | None = None  # the one set of process resources (app is the only place for such a global)
_registrars: list[Callable[[Builder], None]] | None = None
_ports: dict[str, type] | None = None  # field name -> port, read once from the annotations of OrgRuntime


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
    """Dotted names of the ``orgmcp.app.wire_*`` modules, sorted: each declares the providers of one package."""
    package = __package__ or "orgmcp.app"
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
    global _ports
    if _ports is None:
        _ports = {name: port for name, port in get_type_hints(OrgRuntime).items() if name != "root"}
    return _ports


def open_runtime(root: Path, overrides: Mapping[type, object] | None = None) -> OrgRuntime:
    """The runtime of the organization at ``root`` (resolved by the caller). Constructors do no I/O; ``overrides`` replace ports."""
    builder = Builder(root, overrides)
    builder.provide(ProcessResources, lambda _: process_resources())
    for register in registrars():
        register(builder)
    values: dict[str, object] = {"root": root}
    for name, port in runtime_ports().items():
        values[name] = builder.get(port)
    return OrgRuntime(**values)  # type: ignore[arg-type]
