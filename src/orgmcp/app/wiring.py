"""The composition root's public entry points (ARCHITECTURE.md 6.1). RED skeleton (M2)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from ._builder import Builder
from ._resources import ProcessResources
from .runtime import OrgRuntime


def new_process_resources() -> ProcessResources:
    """A fresh set of process resources (the plain ones, or the patch-point ones while ``_compat.ENABLED``)."""
    raise NotImplementedError("red: M2")


def process_resources() -> ProcessResources:
    """The resources of this process (created on the first call)."""
    raise NotImplementedError("red: M2")


def wire_modules() -> list[str]:
    """Dotted names of the ``orgmcp.app.wire_*`` modules, sorted: each declares the providers of one package."""
    raise NotImplementedError("red: M2")


def registrars() -> list[Callable[[Builder], None]]:
    """The ``register`` function of every ``wire_*`` module, in the order of ``wire_modules``."""
    raise NotImplementedError("red: M2")


def open_runtime(root: Path, overrides: Mapping[type, object] | None = None) -> OrgRuntime:
    """The runtime of the organization at ``root`` (resolved by the caller). Constructors do no I/O; ``overrides`` replace ports."""
    raise NotImplementedError("red: M2")
