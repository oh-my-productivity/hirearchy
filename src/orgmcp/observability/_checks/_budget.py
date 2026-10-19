"""(b) Budget conservation."""

from __future__ import annotations

from collections.abc import Sequence

from ...agents import AgentDirectory, RetiredArchive
from ...budget import BudgetQuery
from ...kernel import JsonObject
from ...mail import MessageFile
from ...runs import RunLogReader
from .._ports import IntegrityCheck


class BudgetConserved(IntegrityCheck):
    def __init__(self, agents: AgentDirectory, budgets: BudgetQuery, run_logs: RunLogReader, archive: RetiredArchive) -> None:
        self._agents, self._budgets, self._run_logs, self._archive = agents, budgets, run_logs, archive

    def run(self, files: Sequence[MessageFile], now: float) -> JsonObject:
        raise NotImplementedError("red: C-obs-2")
