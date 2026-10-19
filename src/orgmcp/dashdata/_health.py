"""``CachedHealthQuery``: what is happening now, which agents are flagged, and the integrity checks on demand."""

from __future__ import annotations

from datetime import datetime
from typing import cast

from ..health import HealthAnalyzer
from ..kernel import ROOT, JsonObject, fmt_dur
from ..observability import IntegrityChecks, NowQueries, ObservabilityRenderer
from ._const import HEALTH_TTL
from ._data import HealthView, Snapshot
from ._ports import ReadableEvents
from ._text import clean_text, pause_text
from .api import DashboardState, HealthQuery, SnapshotQuery


class CachedHealthQuery(HealthQuery):
    def __init__(self, state: DashboardState, snapshots: SnapshotQuery, now: NowQueries, renderer: ObservabilityRenderer,
                 analyzer: HealthAnalyzer, checks: IntegrityChecks, events: ReadableEvents) -> None:
        self._state = state
        self._snapshots = snapshots
        self._now = now
        self._renderer = renderer
        self._analyzer = analyzer
        self._checks = checks
        self._events = events

    def health(self, snap: Snapshot | None = None) -> HealthView:
        self._state.refresh()
        snap = snap or self._state.snap or self._snapshots.snapshot()
        found = snap
        return self._state.memoised("health", snap.sig, HEALTH_TTL, lambda: self._health(found))

    def _health(self, snap: Snapshot) -> HealthView:
        now = snap.at
        try:
            now_text = self._now_text(self._now.now_view(now))
        except Exception as exc:  # noqa: BLE001
            now_text = f"(observe now failed: {type(exc).__name__}: {exc})"
        flagged: list[tuple[str, list[tuple[str, str]]]] = []
        try:
            report = self._analyzer.org_health(ROOT, now)
            flagged = [(h.addr, list(h.flags.items())) for h in report.flagged]
            summary = f"{len(report.agents)} agent(s), {len(flagged)} flagged"
        except Exception as exc:  # noqa: BLE001
            summary = f"health failed: {type(exc).__name__}: {exc}"
        return HealthView(clean_text(now_text), flagged, summary, now)

    def _now_text(self, v: JsonObject) -> str:
        """The text of the now view with the two things that differ from the rest of the dashboard put right: agents that
        are paused / out of budget are not 'queued' (they are listed apart), and the recent errors are readable lines."""
        queued = cast("list[JsonObject]", v.get("queued") or [])
        held = [q for q in queued if str(q["reason"]).startswith("paused") or q["reason"] == "no budget"]
        errors = cast("JsonObject", v.get("errors_15m") or {})
        errs = cast("list[JsonObject]", errors.get("events") or [])
        v2 = {**v, "queued": [q for q in queued if q not in held],
              "errors_15m": {**errors, "events": []}}
        lines = self._renderer.render_now(v2).split("\n")
        if held:
            at = next((i for i, ln in enumerate(lines) if ln.startswith("waiting on you")), len(lines))
            extra = [f"not started, with unread mail ({len(held)}):"]
            for q in held:
                reason = str(q["reason"])
                why = pause_text(reason.removeprefix("paused: ")) if reason.startswith("paused") else "out of budget"
                waiting = q.get("waiting_s")
                age = f", oldest {fmt_dur(cast('float', waiting) * 1000)}" if waiting is not None else ""
                extra.append(f"  {q['agent']}: {q['unread']} unread{age} - {why}")
            lines[at:at] = extra
        if errs:
            at_ = next((i for i, ln in enumerate(lines) if ln.startswith("errors in the last 15 min")), None)
            if at_ is not None:
                lines[at_ + 1:at_ + 1] = ["  " + x.text for x in self._events.lines(errs, actor=True)]
        return "\n".join(lines)

    def run_check(self) -> tuple[datetime, str, bool]:
        """The integrity checks (on demand): (when, rendered text, all passed)."""
        now = self._state.now()
        try:
            res = self._checks.check(now)
            self._state.check_result = (now, self._renderer.render_check(res), bool(res["ok"]))
        except Exception as exc:  # noqa: BLE001
            self._state.check_result = (now, f"the check could not run: {type(exc).__name__}: {exc}", False)
        return self._state.check_result
