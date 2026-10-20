"""When a team last did anything, from the names and modification times of its files (moved from ``progress._last_activity``)."""

from __future__ import annotations

import os
from collections.abc import Sequence
from datetime import datetime, timezone

from ..kernel import OrgLayout, stamp_of
from ._ports import TeamActivity


class FsTeamActivity(TeamActivity):
    """The newest message or run in the team's mailboxes and run logs (from file names and mtimes: no parsing)."""

    def __init__(self, layout: OrgLayout) -> None:
        self._layout = layout

    def newest(self, team: Sequence[str]) -> datetime | None:
        newest: datetime | None = None
        for a in team:
            d = self._layout.agent_dir(a)
            for box in ("inbox", "inflight", "read", "sent"):
                try:
                    names = os.listdir(d / box)
                except OSError:
                    continue
                for n in names:
                    t = None if n.startswith(".") else stamp_of(n)
                    if t and (newest is None or t > newest):
                        newest = t
            try:
                for n in os.listdir(d / "runs"):
                    if n.endswith(".log") and not n.startswith("."):
                        t = datetime.fromtimestamp(os.stat(d / "runs" / n).st_mtime, timezone.utc)
                        if newest is None or t > newest:
                            newest = t
            except OSError:
                continue
        return newest
