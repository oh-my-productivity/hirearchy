"""What the legacy ``upgrade_rules`` needs of the ``Org`` it is given (a feature may not import the facade, so it names the part it uses)."""

from __future__ import annotations

from typing import Protocol

from .api import RulesUpgrader


class UpgradedRuntime(Protocol):
    @property
    def rules_upgrader(self) -> RulesUpgrader: ...


class UpgradedOrg(Protocol):
    @property
    def runtime(self) -> UpgradedRuntime: ...

