"""The row of an agent in the tree: who it is, what it holds, what state it is in."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from ..agents import CharterReader
from ..access import ModelResolver
from ..budget import BudgetQuery
from ..eligibility import PauseStore
from ..kernel import ROOT, Message, depth, parent, stamp_of
from ..mail import MailboxReader, TaskQuery
from ..runs import RunLogReader, RunRegistry
from ..services import ServiceCatalog
from ._const import GLYPHS
from ._data import AgentRow
from ._ports import AgentProfile, AgentWork, Elapsed, RowSource
from ._states import classify


class CharterProfile(AgentProfile):
    def __init__(self, charters: CharterReader, models: ModelResolver) -> None:
        self._charters = charters
        self._models = models

    def profile(self, addr: str) -> tuple[str, str]:
        meta, _ = self._charters.charter(addr)
        return str(meta.get("role") or "?"), str(meta.get("model") or "").strip() or self._models.default_model()


class MailAgentWork(AgentWork):
    def __init__(self, mailbox: MailboxReader, tasks: TaskQuery) -> None:
        self._mailbox = mailbox
        self._tasks = tasks

    def running(self, addr: str) -> bool:
        return self._mailbox.has_inflight(addr)

    def unread(self, addr: str) -> int:
        return self._mailbox.unread(addr)

    def open_tasks(self, addr: str) -> list[Message]:
        return self._tasks.open_tasks(addr)

    def outstanding(self, addr: str) -> list[Message]:
        return self._tasks.outstanding(addr)


class LogRunElapsed(Elapsed):
    """How long a run has been going: from the registry's start time, else from the name of its log, else of the agent's latest run log."""

    def __init__(self, registry: RunRegistry, runs: RunLogReader) -> None:
        self._registry = registry
        self._runs = runs

    def since_start(self, running: Sequence[str], now: datetime) -> dict[str, float | None]:
        records = self._registry.all()
        return {a: self._elapsed(a, records.get(a), now) for a in running}

    def _elapsed(self, a: str, rec: dict[str, object] | None, now: datetime) -> float | None:
        rec = rec or {}
        started = rec.get("started")
        if isinstance(started, (int, float)) and not isinstance(started, bool):
            t0: datetime | None = datetime.fromtimestamp(started, timezone.utc)
        else:
            stem = Path(str(rec.get("log", ""))).stem if rec.get("log") else None
            if stem is None:
                logs = self._runs.files(a)
                stem = logs[-1].stem if logs else None
            t0 = stamp_of(stem) if stem else None
        return max(0.0, (now - t0).total_seconds()) if t0 else None


class StateRows(RowSource):
    """One row per agent: its role and model, what it holds (mail, tasks, budget, runs, flag, services) and the one state those make."""

    def __init__(self, profile: AgentProfile, work: AgentWork, pauses: PauseStore, budgets: BudgetQuery, runs: RunLogReader,
                 services: ServiceCatalog, elapsed: Elapsed) -> None:
        self._profile = profile
        self._work = work
        self._pauses = pauses
        self._budgets = budgets
        self._runs = runs
        self._services = services
        self._elapsed = elapsed

    def running(self, agents: Sequence[str]) -> list[str]:
        return [a for a in agents if self._work.running(a)]

    def root(self) -> AgentRow:
        return AgentRow(ROOT, ROOT, 0, None, "you (the human, root of the organization)", "", "you", GLYPHS["you"], "you", None,
                        unread=self._work.unread(ROOT), delegated=len(self._work.outstanding(ROOT)))

    def build(self, agents: Sequence[str], running: Sequence[str], now: datetime, scheduler_up: bool, free: int,
              max_parallel: int) -> dict[str, AgentRow]:
        elapsed = self._elapsed.since_start(running, now)
        return {a: self._row(a, a in running, elapsed, scheduler_up, free, max_parallel) for a in agents}

    def _row(self, a: str, running: bool, elapsed_of: dict[str, float | None], sched_up: bool, free: int, max_parallel: int) -> AgentRow:
        role, model = self._profile.profile(a)
        unread = self._work.unread(a)
        paused = self._pauses.paused(a)
        budget = self._budgets.budget(a) or 0
        open_n = len(self._work.open_tasks(a))
        out_n = len(self._work.outstanding(a))
        elapsed = elapsed_of.get(a) if running else None
        st = classify(running=running, unread=unread, paused=paused, budget=budget, open_tasks=open_n, delegated=out_n,
                      scheduler_up=sched_up, free_slots=free, max_parallel=max_parallel, elapsed_s=elapsed)
        kind, word, reason = st.kind, st.word, st.reason
        behind = unread if running else 0
        return AgentRow(
            addr=a, name=a.rsplit("/", 1)[-1], depth=depth(a), parent=parent(a), role=role, model=model, kind=kind,
            glyph=GLYPHS[kind], word=word, budget=budget, unread=unread, open_tasks=open_n, delegated=out_n,
            runs_used=self._runs.count(a), paused=paused, elapsed_s=elapsed, reason=reason, queued_behind=behind,
            services=self._services.service_names(a), main=st.main, note=st.note, short=st.short,
        )
