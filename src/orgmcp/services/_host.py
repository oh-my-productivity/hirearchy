"""What the legacy functions of ``services`` need of the ``Org`` they are given (a feature may not import the facade, so it names the parts it uses)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from ..dispatch import ReworkContext
from ..kernel import Message
from .api import ContractNormalizer, ServiceCatalog, ServiceCommands, ServiceHints, ServiceStore


class ServicesRuntime(Protocol):
    @property
    def service_catalog(self) -> ServiceCatalog: ...

    @property
    def service_commands(self) -> ServiceCommands: ...

    @property
    def service_hints(self) -> ServiceHints: ...

    @property
    def service_store(self) -> ServiceStore: ...

    @property
    def contract_normalizer(self) -> ContractNormalizer: ...

    @property
    def rework_context(self) -> ReworkContext: ...


class RuntimeOwner(Protocol):
    @property
    def runtime(self) -> ServicesRuntime: ...


class OrgPlace(Protocol):
    @property
    def root(self) -> Path: ...

    def dir(self, addr: str) -> Path: ...


class OrgAgents(Protocol):
    def exists(self, addr: str) -> bool: ...

    def parent(self, addr: str) -> str | None: ...

    def subtree(self, addr: str) -> list[str]: ...

    def require(self, addr: str) -> str: ...


class OrgMail(Protocol):
    def sent(self, addr: str) -> list[Message]: ...

    def received(self, addr: str) -> list[Message]: ...

    def open_tasks(self, addr: str) -> list[Message]: ...


class OrgSettingsView(Protocol):
    @property
    def config(self) -> Mapping[str, object]: ...


class ServicesOrg(RuntimeOwner, OrgPlace, OrgAgents, OrgMail, OrgSettingsView, Protocol):
    """The ports of the runtime, and the few reads of the history of the requests that the part not moved yet (``reflection``) still makes through
    the ``Org``: its place, its agents, its mailboxes and its settings."""
