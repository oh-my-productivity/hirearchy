"""``FileHealthAnalyzer``: the metrics and flags of each agent, from its message files and run logs."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..eligibility import AgentStates, PauseStore
from ..kernel import ROOT, Clock
from ..mail import MailboxReader
from ..runs import RunLogReader
from ._ports import ClientRework, HireDates, RunCount
from .api import AgentHealth, HealthAnalyzer, HealthThresholds, OrgHealth


class FileHealthAnalyzer(HealthAnalyzer):
    def __init__(
        self, agents: AgentDirectory, mail: MailboxReader, runs: RunLogReader, run_count: RunCount, budgets: BudgetQuery,
        pauses: PauseStore, states: AgentStates, thresholds: HealthThresholds, rework: ClientRework, hired: HireDates, clock: Clock,
    ) -> None:
        pass  # red: C-health

    def agent_health(self, addr: str, now: datetime | None = None, limits: Mapping[str, float] | None = None) -> AgentHealth:
        raise NotImplementedError("red: C-health")

    def org_health(self, root: str = ROOT, now: datetime | None = None) -> OrgHealth:
        raise NotImplementedError("red: C-health")
