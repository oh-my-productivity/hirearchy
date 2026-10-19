"""The ports the dashboard consumes (they belong to it, not to ``dashdata``): the five queries as one object, and the two things the launcher is given."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from ..dashdata import AgentDetailQuery, EventFeed, HealthQuery, RequestQuery, ServiceQuery, SnapshotQuery


@runtime_checkable
class DashboardQueries(SnapshotQuery, AgentDetailQuery, RequestQuery, ServiceQuery, HealthQuery, Protocol):
    """What the app asks of an organization: the five queries of ``dashdata`` (they share ONE cache, so they are asked from one thread at a time) and
    the event log they keep in memory, as far as it is read (``None`` before the first snapshot)."""

    @property
    def feed(self) -> EventFeed | None:
        """The event feed of the dashboard; created by the first ``snapshot()``, polled by the following ones."""
        ...


@runtime_checkable
class QueriesOpener(Protocol):
    def open(self, root: Path) -> DashboardQueries:
        """The queries over the organization at ``root`` (read-only, lenient with what it cannot read). Not an organization: an ``OrgError``."""
        ...


@runtime_checkable
class ScreenRunner(Protocol):
    def run(self, queries: DashboardQueries, interval: float) -> None:
        """Take over the terminal with the dashboard of ``queries`` until the user quits."""
        ...
