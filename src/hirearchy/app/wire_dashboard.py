"""The dashboard over the ports of an organization (ARCHITECTURE.md 6.3): the queries of one dashboard, the opener of them, the launcher.

The dashboard needs no port of the runtime of its own (``NOT_A_FIELD`` of ``fields_dashboard``): the five queries and the state they share are the
fields of ``fields_dashdata``, built over the lenient ports of ``wire_dashdata.dashboard_runtime``, and ``ComposedQueries`` is the one object the app asks. The
Textual app is made by the screen (``TextualScreenRunner``), never by the wiring, so that opening an organization (and refusing a directory that is none)
happens before the terminal is taken over.

Nothing of the dashboard package is imported here when this module is loaded: it loads Textual, and every runtime loads every ``wire_*`` module. The functions
import what they need when a dashboard is asked for (as ``wire_mcp_server`` does for the MCP framework).

Read-only, like the queries: the dashboard writes nothing inside the organization and emits no event.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ._builder import Builder

if TYPE_CHECKING:
    from ..dashboard import DashboardLauncher
    from ..dashboard._ports import DashboardQueries, ScreenRunner

__all__ = ["dashboard_launcher", "queries_of", "register"]


def register(b: Builder) -> None:
    """The dashboard has no port of its own (see the module docstring)."""


def queries_of(root: str | Path, now: Callable[[], datetime] | None = None, scheduler_ttl: float = 3.0) -> DashboardQueries:
    """The queries of one dashboard of the organization at ``root`` (``OrgError`` when it is not one). ``now``: the time it shows."""
    from ._dashboard_queries import RuntimeQueriesOpener

    return RuntimeQueriesOpener(now, scheduler_ttl).open(Path(root))


def dashboard_launcher(screens: ScreenRunner | None = None) -> DashboardLauncher:
    """The launcher of ``hirearchy dash``: it opens the queries of a root and puts them on ``screens`` (default: the Textual app)."""
    from ..dashboard._launcher import TextualDashboardLauncher, TextualScreenRunner
    from ._dashboard_queries import RuntimeQueriesOpener

    return TextualDashboardLauncher(RuntimeQueriesOpener(), screens or TextualScreenRunner())
