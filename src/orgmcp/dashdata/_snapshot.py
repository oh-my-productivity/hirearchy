"""``CachedSnapshotQuery``: the picture of the organization now."""

from __future__ import annotations

import time

from ..agents import AgentDirectory
from ..attention import HumanQueue
from ..kernel import ROOT
from ..settings import OrgSettings
from ._data import AgentRow, Snapshot
from ._ports import OrgSite, RowSource, SchedulerViews
from ._tree import arrange
from .api import DashboardState, SnapshotQuery


class CachedSnapshotQuery(SnapshotQuery):
    """Header counts, the scheduler and one row per agent, in one pass over the ports. A refresh is cheap because the ports it asks are
    cached by what changed on disk (the caching decorators of the dashboard) and the directory times are looked at once (the probe)."""

    def __init__(self, state: DashboardState, scheduler: SchedulerViews, agents: AgentDirectory, settings: OrgSettings, rows: RowSource,
                 queue: HumanQueue, site: OrgSite) -> None:
        self._state = state
        self._scheduler = scheduler
        self._agents = agents
        self._settings = settings
        self._rows = rows
        self._queue = queue
        self._site = site

    def snapshot(self) -> Snapshot:
        t0 = time.perf_counter()
        state, now = self._state, self._state.now()
        state.refresh()
        feed = state.following(now)
        agents = self._agents.agents()
        max_parallel = int(self._settings.number("max_parallel", int))
        sched = self._scheduler.view(now)
        inflight = self._rows.running(agents)
        free = max_parallel - len(inflight)
        sched_up = sched.state == "running"
        rows: dict[str, AgentRow] = {ROOT: self._rows.root()}
        rows.update(self._rows.build(agents, inflight, now, sched_up, free, max_parallel))
        order = arrange(rows, agents)
        needs = self._queue.items()
        retired = self._site.retired()
        sig = self._site.signature(agents)
        snap = Snapshot(
            org_name=self._site.name(), root=self._site.root(), at=now, scheduler=sched, max_parallel=max_parallel, agents=rows,
            order=order, running=len(inflight), queued=sum(1 for a in agents if rows[a].kind == "queued"), needs_you=needs,
            errors_15m=feed.error_count(now), last_event=feed.last_ts, events_seen=feed.any,
            bad_files=self._site.unreadable(), retired=retired, sig=sig,
        )
        snap.ms = (time.perf_counter() - t0) * 1000
        state.snap = snap
        return snap
