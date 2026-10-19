"""What the legacy functions need of the ``Org`` they are given (a feature may not import the facade, so it names the parts it uses)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from ..agents import AgentDirectory
from ..dispatch import TaskAssigner
from ..hierarchy import Hiring, Retirement
from ..kernel import ROOT, JsonObject
from ..services import ServiceCommands
from ..snapshots import OrgSnapshotter
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


class OrgPorts(Protocol):
    """The ports of the runtime that an application builds with."""

    @property
    def hiring(self) -> Hiring: ...

    @property
    def retirement(self) -> Retirement: ...

    @property
    def agents(self) -> AgentDirectory: ...

    @property
    def service_commands(self) -> ServiceCommands: ...

    @property
    def task_assigner(self) -> TaskAssigner: ...

    @property
    def snapshotter(self) -> OrgSnapshotter: ...


class OrgWithPorts(OrgFacts, Protocol):
    """An ``Org`` that can be applied to: it has the ports of its runtime."""

    @property
    def runtime(self) -> OrgPorts: ...


class HostOrgContext(OrgContext):
    """The organization as the ``Org`` object says it is (its ``config`` may be a lenient one, as in the dashboard)."""

    def __init__(self, org: OrgFacts) -> None:
        self._org = org

    def config(self) -> JsonObject:
        return dict(self._org.config)

    def root(self) -> Path | None:
        return self._org.root

    def exists(self, addr: str) -> bool:
        return self._org.exists(addr)

    def service_names(self) -> set[str]:
        return {n for kid in self._org.children(ROOT) for n in self._org.service_names(kid)}
