"""What the legacy functions need of the ``Org`` they are given (a feature may not import the facade, so it names the parts it uses)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from ..kernel import JsonObject
from ._protocols import OrgContext


class OrgFacts(Protocol):
    """The few facts about the organization that the legacy functions read from the ``Org`` itself."""

    @property
    def root(self) -> Path: ...

    @property
    def config(self) -> Mapping[str, object]: ...

    def exists(self, addr: str) -> bool: ...

    def children(self, addr: str) -> list[str]: ...

    def service_names(self, addr: str) -> list[str]: ...


class HostOrgContext(OrgContext):
    """The organization as the ``Org`` object says it is (its ``config`` may be a lenient one, as in the dashboard)."""

    def __init__(self, org: OrgFacts) -> None:
        self._org = org

    def config(self) -> JsonObject:
        raise NotImplementedError("red: C-blueprint-1")

    def root(self) -> Path | None:
        raise NotImplementedError("red: C-blueprint-1")

    def exists(self, addr: str) -> bool:
        raise NotImplementedError("red: C-blueprint-1")

    def service_names(self) -> set[str]:
        raise NotImplementedError("red: C-blueprint-1")
