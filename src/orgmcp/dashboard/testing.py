"""Fakes for ``dashboard``: queries that answer what they are told (a small organization that is only data), an opener of queries over a set of
directories, a screen that records what it was asked to show, a launcher that records what it was asked to run, and the registry the contract suites iterate
over.

``fixed_queries`` / ``small_snapshot`` are what the app is given when its test is not about what the files say: the five queries of ``dashdata`` answer
the rows they were given, over a state that has an event feed in memory, so building an app on them touches no file (its root is ``/memory/org``, which
does not exist). ``DashboardWorld`` is the app on top of them with the means to change what they answer.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..dashdata import AgentDetail, AgentRow, HealthView, RequestRow, RunLog, SchedulerView, Section, ServiceRow, Snapshot
from ..dashdata.testing import (
    FixedAgentDetailQuery,
    FixedEventFeedFactory,
    FixedHealthQuery,
    FixedRequestQuery,
    FixedServiceQuery,
    FixedSnapshotQuery,
    MemoryDashboardState,
    MemoryEventFeed,
)
from ..kernel import OrgError
from ..kernel.testing import FakeClock
from ._launcher import TextualDashboardLauncher
from ._ports import DashboardQueries, QueriesOpener, ScreenRunner
from ._queries import ComposedQueries
from .api import DashboardLauncher

ORG_ROOT = Path("/memory/org")  # does not exist: nothing that is given this root can read it
SHOWN = datetime.fromisoformat("2026-10-18T10:06:40+00:00")

# ------------------------------------------------------------------------------ what the queries answer


def agent_row(
    addr: str, kind: str = "idle", word: str = "idle", glyph: str = "○", budget: int | None = 3, parent: str | None = "root", depth: int = 1, **fields: object,
) -> AgentRow:
    """The row of an agent in the tree; ``main`` is ``word``."""
    name = addr.rpartition("/")[2]
    row = AgentRow(addr, name, depth, parent, f"{name} role", "claude-sonnet-5.5", kind, glyph, word, budget, main=word, short=word)
    for key, value in fields.items():
        setattr(row, key, value)
    return row


def small_snapshot(root: Path = ORG_ROOT) -> Snapshot:
    """``root`` -> ``ops`` (running 1m12s) -> ``ops/eng`` (queued), and ``scribe`` (idle); one thing needs root."""
    rows = [
        agent_row("root", "you", "you", "★", None, None, 0, children=["ops", "scribe"]),
        agent_row("ops", "running", "running 1m12s", "▶", 3, children=["ops/eng"], below_queued=1),
        agent_row("ops/eng", "queued", "queued: starts on the next tick", "◔", 2, "ops", 2),
        agent_row("scribe", "idle", "idle", "○", 0),
    ]
    return Snapshot(
        "memo", str(root), SHOWN, SchedulerView("running", 4242, "2026-10-18 10:00:00Z", "until_done", 400.0, 3.0), 2,
        {r.addr: r for r in rows}, [r.addr for r in rows], running=1, queued=1, needs_you=[("m-1", 'note from ops "Need approval": May I?')], errors_15m=0,
    )


def request_row(task_id: str = "t-1", title: str = "Write the report", assignee: str = "ops") -> RequestRow:
    return RequestRow(task_id, title, assignee, None, None, "working", "working", assignee, 1, 4, "runs 1 of 4", 12.0, SHOWN, 0)


def health_view() -> HealthView:
    return HealthView("scheduler: running pid 4242", [("scribe", [("out_of_budget", "no budget left")])], "3 agent(s), 1 flagged", SHOWN)


# ------------------------------------------------------------------------------ the queries


def detail(addr: str, *overview: str, snap: Snapshot | None = None) -> AgentDetail:
    """What the Overview tab of ``addr`` says: ``overview`` is its lines under one title."""
    row = (snap or small_snapshot()).agents.get(addr)
    return AgentDetail(addr, row, [Section(addr, list(overview))], [], RunLog(note="this agent has not run yet"), "(no memory yet)", f"role: {addr}", [])


def fixed_queries(
    snapshot: Snapshot | None = None, requests: Sequence[RequestRow] = (), services: Sequence[ServiceRow] = (), feed: MemoryEventFeed | None = None,
    details: Mapping[str, AgentDetail] | None = None, traces: Mapping[str, str] | None = None, service_details: Mapping[tuple[str, str], list[Section]] | None = None,
) -> ComposedQueries:
    """The five queries over rows put in, and a state whose event feed is in memory (it exists from the start, as it does after the first snapshot)."""
    snap = snapshot or small_snapshot()
    state = MemoryDashboardState(FakeClock(), FixedEventFeedFactory(feed or MemoryEventFeed()), lambda: SHOWN)
    state.following(SHOWN)
    return ComposedQueries(
        FixedSnapshotQuery(snap), FixedAgentDetailQuery(details), FixedRequestQuery(requests, traces=traces), FixedServiceQuery(services, service_details),
        FixedHealthQuery(health_view(), (SHOWN, "(a) PASS messages intact", True)), state,
    )


# ------------------------------------------------------------------------------ the launcher and what it is given


class MemoryQueriesOpener(QueriesOpener):
    """The organizations are the set ``organizations`` of directories (no file is looked at); ``opened`` lists, in order, the queries it made and for which root."""

    def __init__(self, organizations: set[Path] | None = None) -> None:
        self.organizations = organizations if organizations is not None else set()
        self.opened: list[tuple[Path, DashboardQueries]] = []

    def open(self, root: Path) -> DashboardQueries:
        if root not in self.organizations:
            raise OrgError(f"not an organization (no ORG.md): {root}")
        queries = fixed_queries(small_snapshot(root))
        self.opened.append((root, queries))
        return queries


class RecordingScreens(ScreenRunner):
    """Shows nothing: ``runs`` lists, in order, the queries and the interval it was asked to show."""

    def __init__(self) -> None:
        self.runs: list[tuple[DashboardQueries, float]] = []

    def run(self, queries: DashboardQueries, interval: float) -> None:
        self.runs.append((queries, interval))


class FakeDashboardLauncher(DashboardLauncher):
    """Runs nothing: ``launched`` lists, in order, the root and the interval it was asked for; a root that is not in ``organizations`` is refused as the real one does."""

    def __init__(self, organizations: set[Path] | None = None) -> None:
        self.organizations = organizations if organizations is not None else set()
        self.launched: list[tuple[Path, float]] = []

    def run_dashboard(self, root: Path, interval: float = 2.0) -> None:
        if root not in self.organizations:
            raise OrgError(f"not an organization (no ORG.md): {root}")
        self.launched.append((root, interval))


# ------------------------------------------------------------------------------ the worlds the contract suite iterates over


@dataclass
class LauncherWorld:
    """A launcher, an organization it can show (``root``), a directory that is none (``elsewhere``), and what has been put on the screen so far."""

    launcher: DashboardLauncher
    root: Path
    elsewhere: Path
    shown: Callable[[], list[tuple[Path, float]]]


def textual_launcher(tmp_path: Path) -> LauncherWorld:
    """The Textual launcher over an opener of queries (a set of directories) and a screen that records what it was asked to show."""
    root, elsewhere = tmp_path / "org", tmp_path / "elsewhere"
    opener, screens = MemoryQueriesOpener({root}), RecordingScreens()

    def shown() -> list[tuple[Path, float]]:
        return [(next(path for path, made in opener.opened if made is queries), interval) for queries, interval in screens.runs]

    return LauncherWorld(TextualDashboardLauncher(opener, screens), root, elsewhere, shown)


def fake_launcher(tmp_path: Path) -> LauncherWorld:
    """The launcher that only records."""
    root, elsewhere = tmp_path / "org", tmp_path / "elsewhere"
    fake = FakeDashboardLauncher({root})
    return LauncherWorld(fake, root, elsewhere, lambda: list(fake.launched))


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    DashboardLauncher: [textual_launcher, fake_launcher],
}

__all__ = [
    "FakeDashboardLauncher", "IMPLEMENTATIONS", "LauncherWorld", "MemoryQueriesOpener", "ORG_ROOT", "RecordingScreens", "SHOWN", "agent_row", "detail",
    "fake_launcher", "fixed_queries", "health_view", "request_row", "small_snapshot", "textual_launcher",
]
