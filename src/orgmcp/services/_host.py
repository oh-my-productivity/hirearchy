"""What the legacy functions of ``services`` need of the ``Org`` they are given (a feature may not import the facade, so it names the parts it uses)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..dispatch import ReworkContext
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
    def dir(self, addr: str) -> Path: ...


class ServicesOrg(RuntimeOwner, OrgPlace, Protocol):
    """The ports of the runtime, and the place of an agent (``service_dir``): all that the legacy functions need of the ``Org`` they are given."""
