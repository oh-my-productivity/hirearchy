"""``ArchivedRunTotal``: runs ever used in the organization (moved from ``review.total_runs``)."""

from __future__ import annotations

from ..agents import AgentDirectory, RetiredArchive
from ..runs import RunLogReader
from ._ports import RunTotal


class ArchivedRunTotal(RunTotal):
    def __init__(self, agents: AgentDirectory, runs: RunLogReader, archive: RetiredArchive) -> None:
        self._agents = agents
        self._runs = runs
        self._archive = archive

    def total(self) -> int:
        """Runs ever used across the organization, counted from the run logs (so a restart does not reset it).

        Retired agents are included, so retiring never moves the counter backwards (and never postpones a review).
        """
        return sum(self._runs.count(a) for a in self._agents.agents()) + self._archive.run_count()
