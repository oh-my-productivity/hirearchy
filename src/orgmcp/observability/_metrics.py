"""The metrics over a time window: runs, tool calls, refusals, messages, what the scheduler and the agents went through."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import cast

from ..eventlog import EventReader
from ..kernel import Clock, JsonObject, OrgError, aware, clip_line, norm
from ._messages import Msg
from ._ports import MessageHistory, RunCollection
from ._pure import normalize_refusal, parse_when
from ._runs import RunRec, run_events
from ._util import iso, stats
from .api import MetricQueries

DIMENSIONS = ("agent", "tool", "service", "trace")
_OUTCOMES = ("ok", "failed", "timeout", "killed", "running", "unknown")


def group_key(by: str, run: RunRec | None, call: JsonObject | None, msgs: Mapping[str, Msg]) -> list[str]:
    """Group keys of a run (``run`` given) or a tool call (``call`` given) for ``by``; [] means no row."""
    if by == "agent":
        return [run.agent] if run is not None else [str(cast(JsonObject, call).get("actor") or "-")]
    if by == "tool":
        return [str(call.get("tool"))] if call is not None else []
    if by == "service":
        if call is not None:
            svc = cast("JsonObject", call.get("args") or {}).get("service")
            return [str(svc)] if svc else ["-"]
        svcs = {msgs[b].service for b in cast(RunRec, run).batch or () if b in msgs and msgs[b].service}
        return sorted(s for s in svcs if s) or ["-"]
    if by == "trace":
        if call is not None:
            return [str(call.get("trace") or "-")]
        return list(cast(RunRec, run).traces or []) or ["-"]
    raise OrgError("by must be one of agent, tool, service, trace")


class DerivedMetricQueries(MetricQueries):
    """Counts, rates and percentiles over ``[since, now]``.

    Runs are the run logs of the window (so counts equal what the files say), with outcome and duration from
    ``run.end`` events (else from the log's closing lines). Percentiles are nearest-rank on the raw durations.
    """

    def __init__(self, events: EventReader, runs: RunCollection, history: MessageHistory, clock: Clock) -> None:
        self._events, self._runs, self._history, self._clock = events, runs, history, clock

    def metrics(self, since: str | datetime | None = "24h", by: str | None = None, now: datetime | None = None, agent: str | None = None) -> JsonObject:
        now = aware(now) or self._clock.now()
        lo = parse_when(since, now) or (now - timedelta(hours=24))
        if by is not None and by not in DIMENSIONS:
            raise OrgError("by must be one of agent, tool, service, trace")
        agent = norm(agent) if agent else None
        later = list(self._events.timed(lo, None))  # run.end of a run that started in the window may come after it
        evs = [(t, ev) for t, ev in later if t <= now]
        runs = self._runs.collect(lo, now, run_events(later))
        if agent:
            runs = [r for r in runs if r.agent == agent]
        calls = [ev for _, ev in evs if ev.get("kind") == "tool.call" and (not agent or ev.get("actor") == agent)]
        outcomes = Counter(r.outcome for r in runs)
        run_ms = [r.duration_ms for r in runs if r.duration_ms is not None]
        queue = [r.queue_ms for r in runs if r.queue_ms is not None]

        tools: dict[str, JsonObject] = {}
        for name in sorted({str(c.get("tool")) for c in calls}):
            mine = [c for c in calls if str(c.get("tool")) == name]
            bad = [c for c in mine if c.get("ok") is False]
            ms = [float(cast(float, c["ms"])) for c in mine if isinstance(c.get("ms"), (int, float))]
            tools[name] = {"calls": len(mine), "refused": len(bad), "refusal_rate": len(bad) / len(mine),
                           "ms": stats(ms), "exceptions": sum(1 for c in bad if c.get("error_type") not in (None, "OrgError"))}
        refused = [c for c in calls if c.get("ok") is False]
        groups: dict[str, JsonObject] = {}
        for c in refused:
            g = groups.setdefault(normalize_refusal(str(c.get("error") or "(no text)")), {"count": 0, "example": c.get("error"), "tools": Counter()})
            g["count"] = cast(int, g["count"]) + 1
            cast("Counter[str]", g["tools"])[str(c.get("tool"))] += 1
        top = sorted(groups.items(), key=lambda kv: (-cast(int, kv[1]["count"]), kv[0]))[:10]

        kinds = Counter(str(ev.get("kind")) for _, ev in evs)
        msgs = self._history.messages()
        in_window = [m for m in msgs.values() if lo <= m.t <= now]
        sched_err = Counter(str(ev.get("phase")) for _, ev in evs if ev.get("kind") == "scheduler.error")
        exits = Counter(clip_line(ev.get("reason"), 80) for _, ev in evs if ev.get("kind") == "scheduler.exit")
        pauses = Counter(clip_line(ev.get("reason"), 40) for _, ev in evs if ev.get("kind") == "agent.pause")
        out: JsonObject = {
            "since": iso(lo), "until": iso(now), "events": sum(kinds.values()), "agent": agent,
            "runs": {"total": len(runs), **{k: outcomes.get(k, 0) for k in _OUTCOMES},
                     "duration_ms": stats(run_ms), "queue_ms": stats(queue)},
            "tool_calls": {"total": len(calls), "refused": len(refused), "refusal_rate": (len(refused) / len(calls)) if calls else 0.0,
                           "by_tool": tools},
            "top_refusals": [{"message": k, "count": v["count"], "example": clip_line(v["example"] or "", 300),
                              "tools": dict(cast("Counter[str]", v["tools"]))} for k, v in top],
            "messages": dict(Counter(m.type for m in in_window)),
            "stalls": kinds.get("stall.nudge", 0), "pauses": {"total": sum(pauses.values()), "by_reason": dict(pauses)},
            "agent_failures": kinds.get("agent.failure", 0), "orphans": kinds.get("run.orphan", 0),
            "scheduler": {"starts": kinds.get("scheduler.start", 0), "errors": dict(sched_err), "exits": dict(exits)},
            "budget_spent": len(runs),
        }
        if by:
            out["by"] = {"dimension": by, "rows": self._rows(by, runs, calls, msgs)}
        return out

    @staticmethod
    def _rows(by: str, runs: list[RunRec], calls: list[JsonObject], msgs: Mapping[str, Msg]) -> list[JsonObject]:
        """The table grouped by ``by``: a row for every key some run or tool call has."""
        rows: dict[str, JsonObject] = {}

        def row(key: str) -> JsonObject:
            return rows.setdefault(key, {"key": key, "runs": [], "ok": 0, "bad": 0, "calls": [], "refused": 0})

        for r in runs:
            for key in group_key(by, r, None, msgs):
                x = row(key)
                cast("list[RunRec]", x["runs"]).append(r)
                x["ok"] = cast(int, x["ok"]) + (r.outcome == "ok")
                x["bad"] = cast(int, x["bad"]) + (r.outcome in ("failed", "timeout", "killed"))
        for c in calls:
            for key in group_key(by, None, c, msgs):
                x = row(key)
                cast("list[JsonObject]", x["calls"]).append(c)
                x["refused"] = cast(int, x["refused"]) + (c.get("ok") is False)
        table: list[JsonObject] = []
        for key, x in sorted(rows.items()):
            x_runs, x_calls = cast("list[RunRec]", x["runs"]), cast("list[JsonObject]", x["calls"])
            durs = [r.duration_ms for r in x_runs if r.duration_ms is not None]
            ms = [float(cast(float, c["ms"])) for c in x_calls if isinstance(c.get("ms"), (int, float))]
            refused = cast(int, x["refused"])
            table.append({"key": key, "runs": len(x_runs), "ok": x["ok"], "failed": x["bad"],
                          "run_ms": stats(durs), "calls": len(x_calls), "refused": refused,
                          "refusal_rate": (refused / len(x_calls)) if x_calls else 0.0, "call_ms": stats(ms)})
        return table
