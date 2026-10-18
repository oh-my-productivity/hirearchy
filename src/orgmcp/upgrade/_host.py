"""What the legacy ``upgrade_rules`` needs of the ``Org`` it is given (a feature may not import the facade, so it names the part it uses)."""

from __future__ import annotations

from typing import Protocol

from ..settings import OrgDocumentStore


class UpgradedRuntime(Protocol):
    @property
    def documents(self) -> OrgDocumentStore: ...


class UpgradedOrg(Protocol):
    @property
    def runtime(self) -> UpgradedRuntime: ...

    def commit(self, message: str) -> None: ...
