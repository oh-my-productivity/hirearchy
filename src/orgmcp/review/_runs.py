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
        raise NotImplementedError("red: C-review")
