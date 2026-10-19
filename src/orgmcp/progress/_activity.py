"""When a team last did anything, from the names and modification times of its files (moved from ``progress._last_activity``)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ..kernel import OrgLayout
from ._ports import TeamActivity


class FsTeamActivity(TeamActivity):
    def __init__(self, layout: OrgLayout) -> None:
        self._layout = layout

    def newest(self, team: Sequence[str]) -> datetime | None:
        raise NotImplementedError("red: C-progress")
