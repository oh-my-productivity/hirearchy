"""One entry point for the text of every view, and the reading of what a person typed as the target of the events."""

from __future__ import annotations

import re
from datetime import datetime

from ..agents import AgentDirectory
from ..eventlog import EventReader
from ..kernel import ROOT, RUNTIME, JsonObject, OrgError, norm
from ._ports import TargetedEvents
from .api import EventQueries, IntegrityChecks, MetricQueries, NowQueries, ObservabilityRenderer, ObservabilityText, TraceQueries

VIEWS = ("now", "trace", "metrics", "events", "check")
_MSG_ID = re.compile(r"\d{8}T\d{6,}-")


class AgentTargetedEvents(TargetedEvents):
    """The events of the target a person typed: a message id is a trace, an agent (or root or the runtime) an agent, anything else an event kind."""

    def __init__(self, events: EventQueries, agents: AgentDirectory, reader: EventReader) -> None:
        self._events, self._agents, self._reader = events, agents, reader

    def view(self, target: str | None, since: str, errors_only: bool, limit: int, now: datetime | None) -> JsonObject:
        agent = kind = tr = None
        if target:
            if _MSG_ID.match(target):
                tr = target
            elif self._agents.exists(target) or norm(target) in (ROOT, RUNTIME):
                agent = target
            else:
                kind = target
        v = self._events.events_view(since, None, agent, kind, tr, errors_only, limit, now)
        v["any"] = bool(self._reader.files())
        return v


class ViewDispatcher(ObservabilityText):
    """The text of one view by its name: the view from the queries, the text from the renderer."""

    def __init__(
        self, events: TargetedEvents, traces: TraceQueries, metrics: MetricQueries, now: NowQueries, checks: IntegrityChecks,
        renderer: ObservabilityRenderer,
    ) -> None:
        self._events, self._traces, self._metrics, self._now, self._checks, self._renderer = events, traces, metrics, now, checks, renderer

    def observe_text(
        self, view: str = "now", target: str | None = None, since: str = "24h", by: str | None = None, errors_only: bool = False,
        limit: int = 50, now: datetime | None = None, max_lines: int | None = None,
    ) -> str:
        view = (view or "now").strip().lower()
        if view not in VIEWS:
            raise OrgError(f"view must be one of {', '.join(VIEWS)}")
        limit = max(1, int(limit or 50))
        cap = max_lines if max_lines is not None else max(2 * limit, 80)
        if view == "now":
            return self._renderer.render_now(self._now.now_view(now), cap)
        if view == "check":
            return self._renderer.render_check(self._checks.check(now))
        if view == "trace":
            if not target:
                raise OrgError("trace needs target=<root task id> (see progress for the ids)")
            return self._renderer.render_trace(self._traces.trace(target, now), cap)
        if view == "metrics":
            return self._renderer.render_metrics(self._metrics.metrics(since, by, now, agent=target), limit)
        return self._renderer.render_events(self._events.view(target, since, errors_only, limit, now), cap)
