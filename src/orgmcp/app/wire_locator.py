"""Providers of the ``locator`` port (ARCHITECTURE.md 6.1), and the locator that needs no organization to exist."""

from __future__ import annotations

from pathlib import Path

from ..kernel import Environment
from ..kernel._system import OsEnvironment
from ..locator import OrgLocator
from ..locator._env import EnvOrgLocator
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(OrgLocator, lambda b: EnvOrgLocator(b.get(Environment)))


def os_locator() -> OrgLocator:
    """The locator of this process (``Org.find_root`` is static: it runs before any organization is open)."""
    return EnvOrgLocator(OsEnvironment())


def find_org_root(start: str | Path | None = None) -> Path:
    """The organization root for a process that has no runtime yet (``Org.find_root`` is static)."""
    return os_locator().find_root(start)
