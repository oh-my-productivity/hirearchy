"""``CachedAgentDetailQuery``: everything the dashboard shows about one agent."""

from __future__ import annotations

from ..kernel import ROOT, JsonObject
from ._events import EventLine
from ._data import AgentDetail, MsgRow, RunLog, Section, Snapshot
from ._ports import AgentOverviews, AgentTexts, MessageViews, ReadableEvents, RunLogViews
from .api import AgentDetailQuery, DashboardState, SnapshotQuery


class CachedAgentDetailQuery(AgentDetailQuery):
    def __init__(self, state: DashboardState, snapshots: SnapshotQuery, overviews: AgentOverviews, messages: MessageViews, texts: AgentTexts,
                 logs: RunLogViews, events: ReadableEvents) -> None:
        self._state = state
        self._snapshots = snapshots
        self._overviews = overviews
        self._messages = messages
        self._texts = texts
        self._logs = logs
        self._events = events

    def agent_detail(self, addr: str, snap: Snapshot | None = None, raw: bool = False) -> AgentDetail:
        self._state.refresh()
        snap = snap or self._state.snap or self._snapshots.snapshot()
        row = snap.row(addr)
        if row is None:
            return AgentDetail(addr, None, [Section("", [f"{addr}: no such agent (any more)"])], [], RunLog(), "", "", [])
        feed = self._state.feed
        events = feed.matching(agent=addr, limit=300) if feed else []
        return AgentDetail(
            addr=addr, row=row, overview=self._overviews.overview(addr, row, snap, events), messages=self._messages.rows(addr),
            runlog=self.run_log(addr, row.kind == "running") if addr != ROOT else RunLog(note="root is the human: no runs"),
            memory=self._texts.memory(addr), charter=self._texts.charter(addr), events=events,
            activity=self._events.lines(events, me=addr, raw=raw),
        )

    def run_log(self, addr: str, live: bool) -> RunLog:
        return self._logs.run_log(addr, live)

    def message_text(self, row: MsgRow) -> str:
        return self._messages.text(row)

    def message_lookup(self, agent: str, mid: str) -> tuple[str, str, str] | None:
        return self._events.message(agent, mid)

    def event_lines(self, events: list[JsonObject], me: str | None = None, actor: bool = False, raw: bool = False) -> list[EventLine]:
        return self._events.lines(events, me=me, actor=actor, raw=raw)
