"""``HealthReviewPlanner``: who is told what in a review (moved from ``review.review`` and ``review._pairs``)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from ..agents import AgentDirectory
from ..health import HealthAnalyzer
from ..templates import Notices
from ._ports import ReserveCheck, ReviewPlanner, RunTotal
from .api import Review


class HealthReviewPlanner(ReviewPlanner):
    def __init__(self, agents: AgentDirectory, health: HealthAnalyzer, reserve: ReserveCheck, notices: Notices, runs: RunTotal) -> None:
        self._agents = agents
        self._health = health
        self._reserve = reserve
        self._notices = notices
        self._runs = runs

    def plan(self, now: datetime, previous: Mapping[str, list[str]]) -> Review:
        raise NotImplementedError("red: C-review")
