"""Is the process recorded for a run alive."""

from __future__ import annotations

from collections.abc import Mapping

from ...processes import OrphanJudge
from .._ports import LiveRuns


class JudgedLiveRuns(LiveRuns):
    """A recorded process is live when the judge calls it ours (alive and ours to kill) or leaves it in doubt (alive, unverifiable)."""

    def __init__(self, judge: OrphanJudge) -> None:
        self._judge = judge

    def live(self, record: Mapping[str, object] | None) -> bool:
        if not record:
            return False
        return self._judge.judge(record) in ("ours", "doubt")
