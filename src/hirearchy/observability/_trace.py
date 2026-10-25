"""The trace of one request: its messages, runs, tool calls and refusals as a tree in time order, with totals."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import cast

from ..agents import AgentDirectory
from ..eventlog import EventReader
from ..kernel import ROOT, Clock, JsonObject, OrgError, aware, clip_line, parse_time, stamp_of
from ._messages import Msg
from ._ports import MessageHistory, RunCollection, TraceDerivers
from ._pure import ENVELOPE
from ._runs import run_dict, run_events
from ._util import iso, ms_between, plain
from .api import TraceQueries

READ_ONLY_TOOLS = {"inbox", "read", "status", "health", "progress", "quality", "whoami", "services", "observe", "org_read"}
_LIFECYCLE = ("agent.pause", "agent.resume", "agent.failure", "stall.nudge", "run.orphan")


def run_window(task: Msg, result: Msg | None, root_tasks: Sequence[Msg]) -> tuple[str, str | None]:
    """(start, end) of a root task's run window, as 21-character timestamps, exactly as ``progress`` counts runs:
    from the task's creation to its final result (``done``/``failed``) or now, cut where root's next task to the same
    assignee begins."""
    start = task.id[:21]
    end = result.id[:21] if result is not None and result.status in ("done", "failed") else None
    later = [t.id[:21] for t in root_tasks if t.to == task.to and t.id > task.id]
    if later and (end is None or later[0] < end):
        end = later[0]
    return start, end


def in_window(name: str, start: str, end: str | None) -> bool:
    return name[:21] >= start and (end is None or name[:21] <= end)


def calls_summary(calls: Sequence[JsonObject]) -> JsonObject:
    by_tool = Counter(str(c.get("tool")) for c in calls)
    refused = [{"t": c.get("ts"), "tool": c.get("tool"), "error": clip_line(c.get("error") or "", 500),
                "error_type": c.get("error_type"), "actor": c.get("actor")} for c in calls if c.get("ok") is False]
    return {"total": len(calls), "by_tool": dict(by_tool), "refused": refused}


def user_wait(in_trace: Sequence[Msg], evs: Sequence[tuple[datetime, JsonObject]], tid: str, t_end: datetime) -> float:
    """Milliseconds the request spent waiting on root: from each item that needed the human (an unread-and-waking
    blocked/failed result or any waking note/notice addressed to root) to root's next action on the request (a message
    root sent into it, or a state-changing tool call it made for it); open ends run to the end of the request."""
    asks = sorted(m.t for m in in_trace if m.to == ROOT and m.wake and not (m.type == "result" and m.status == "done")
                  and m.type in ("result", "note"))
    acts = sorted([m.t for m in in_trace if m.sender == ROOT]
                  + [t for t, ev in evs if ev.get("kind") == "tool.call" and ev.get("actor") == ROOT and ev.get("trace") == tid
                     and ev.get("tool") not in READ_ONLY_TOOLS])
    spans: list[tuple[datetime, datetime]] = []
    for a in asks:
        nxt = next((x for x in acts if x > a), None)
        spans.append((a, min(nxt, t_end) if nxt else t_end))
    total = 0.0
    cur_lo: datetime | None = None
    cur_hi: datetime | None = None
    for lo, hi in sorted(spans):
        if hi <= lo:
            continue
        if cur_hi is None or lo > cur_hi:
            if cur_hi is not None and cur_lo is not None:
                total += ms_between(cur_lo, cur_hi)
            cur_lo, cur_hi = lo, hi
        else:
            cur_hi = max(cur_hi, hi)
    if cur_hi is not None and cur_lo is not None:
        total += ms_between(cur_lo, cur_hi)
    return total


class DerivedTraceQueries(TraceQueries):
    """One request as a tree, from the message files and run logs (then ``partial``); run and tool-call events add queue wait, durations, tool
    calls and refusals."""

    def __init__(
        self, history: MessageHistory, derivers: TraceDerivers, events: EventReader, runs: RunCollection, agents: AgentDirectory, clock: Clock
    ) -> None:
        self._history, self._derivers, self._events, self._runs, self._agents, self._clock = history, derivers, events, runs, agents, clock

    def _team(self, task: Msg) -> list[str]:
        return [a for a in self._agents.subtree(task.to) if a != ROOT] if self._agents.exists(task.to) else []

    def trace(self, task_id: str, now: datetime | None = None) -> JsonObject:
        now = aware(now) or self._clock.now()
        msgs = self._history.messages()
        root_tasks = sorted((m for m in msgs.values() if m.sender == ROOT and m.type == "task"), key=lambda m: m.id)
        if task_id not in msgs:
            known = ", ".join(t.id for t in root_tasks[-5:]) or "none"
            raise OrgError(f"no message {task_id}. Root's tasks (latest): {known}")
        notes: list[str] = []
        redirect = None  # informational only: it does not make the trace partial
        tid = task_id
        is_root_task = task_id in {t.id for t in root_tasks}
        resolved = self._derivers.derive(msgs).of(task_id)[0]
        if not is_root_task and not resolved:
            raise OrgError(f"{task_id} is not a root task and its request cannot be determined. Root's tasks (latest): "
                           + (", ".join(t.id for t in root_tasks[-5:]) or "none"))
        if resolved and resolved != task_id and resolved in msgs:  # a message of the request, or a rework of an earlier task
            redirect = f"{task_id} belongs to the request {resolved}; showing that"
            notes.append(redirect)
            tid = resolved
        evs = list(self._events.timed(msgs[tid].t - timedelta(seconds=2), None))
        batches = {str(ev["run"]): [str(b) for b in cast("list[object]", ev["batch"])] for _, ev in evs
                   if ev.get("kind") == "run.start" and ev.get("run") and isinstance(ev.get("batch"), list)}
        traces = self._derivers.derive(msgs, batches)
        task = msgs[tid]
        # the request = the root task and every rework of it (a rework's `revises` keeps it in the same trace)
        traces_of_root = {t.id: traces.of(t.id)[0] for t in root_tasks}
        chain = [t for t in root_tasks if t.id == tid or (traces_of_root.get(t.id) == tid and t.id > tid)]

        def result_of(t: Msg) -> Msg | None:
            return max((m for m in msgs.values() if m.to == ROOT and m.type == "result" and m.reply_to == t.id),
                       key=lambda m: m.id, default=None)

        steps = [(t, result_of(t)) for t in chain]
        windows = [run_window(t, r, root_tasks) for t, r in steps]
        result = steps[-1][1]  # the request's state is its latest task's
        final = result is not None and result.status in ("done", "failed")
        state = result.status if result is not None else "open"
        team = self._team(task)
        members = set(team)
        start21, end21 = windows[0][0], windows[-1][1]
        t0 = task.t
        t_end = (stamp_of(result.id) if final and result is not None else None) or now

        def in_windows(name: str) -> bool:
            return any(in_window(name, a, b) for a, b in windows)

        # ---- messages of the request
        items: list[JsonObject] = []
        in_trace: dict[str, tuple[Msg, str]] = {}
        for msg in msgs.values():
            msg_trace, src = traces.of(msg.id)
            if msg_trace == tid:
                in_trace[msg.id] = (msg, src)
            elif msg_trace is None and msg.sender == ROOT and msg.to in members and in_windows(msg.id):
                in_trace[msg.id] = (msg, "window")  # root's grants/notes into the team inside the window carry no trace
        for msg, src in in_trace.values():
            items.append({"t": msg.t, "order": 1, "kind": "message", "agent": msg.sender, "id": msg.id, "type": msg.type,
                          "from": msg.sender, "to": msg.to, "title": msg.title, "status": msg.status, "budget": msg.budget,
                          "trace_source": src})
        derived = sum(1 for _, s in in_trace.values() if s != "recorded")
        if derived:
            notes.append(f"{derived} message(s) have no recorded trace: their request was derived from reply_to/revises/open "
                         "tasks (marked ~)")

        # ---- runs (file truth) enriched with events
        revs = run_events(evs)
        runs = self._runs.team_runs(team, in_windows, revs)
        have_events = any(r.source == "events" for r in runs)
        if runs and not have_events:
            notes.append("partial: no run events for this request (queue waits, tool calls and refusals unknown); "
                         "runs and durations come from the run logs")
        elif any(r.source == "log" for r in runs):
            notes.append("partial: some runs have no events (older runs or events disabled)")

        # ---- tool calls
        calls = [ev for _, ev in evs if ev.get("kind") == "tool.call"]
        run_ids = {r.run for r in runs}
        by_run: dict[str, list[JsonObject]] = defaultdict(list)
        outside: list[JsonObject] = []
        for c in calls:
            if c.get("run") in run_ids and c.get("trace") in (None, tid):
                by_run[str(c["run"])].append(c)
            elif c.get("trace") == tid:
                outside.append(c)
        for r in runs:
            mine = by_run.get(r.run, [])
            shared = [t for t in (r.traces or []) if t != tid]
            items.append({"t": r.start, "order": 2, "kind": "run", "agent": r.agent, **run_dict(r),
                          "tool_calls": calls_summary(mine), "shared_with": shared})
        for c in outside:
            items.append({"t": parse_time(c.get("ts")) or t0, "order": 3, "kind": "tool", "agent": c.get("actor") or ROOT, "tool": c.get("tool"),
                          "ok": c.get("ok"), "ms": c.get("ms"), "error": clip_line(c.get("error") or "", 500),
                          "error_type": c.get("error_type"), "run": c.get("run")})
        # ---- lifecycle events that explain waits (a pause, a stall nudge, an orphaned run) of the request or its team
        for at, ev in evs:
            k = ev.get("kind")
            if k not in _LIFECYCLE:
                continue
            who = ev.get("agent") or ev.get("to")
            stamp = at.strftime("%Y%m%dT%H%M%S%f")
            if ev.get("trace") == tid or (who in members and in_windows(stamp)):
                items.append({"t": at, "order": 4, "kind": "event", "agent": who or "runtime", "event": k,
                              "detail": {x: y for x, y in ev.items() if x not in ENVELOPE}})
        items.sort(key=lambda i: (cast(datetime, i["t"]), cast(int, i["order"])))

        # ---- totals
        user_ms = user_wait([m for m, _ in in_trace.values()], evs, tid, t_end)
        run_ms = sum(r.duration_ms or 0 for r in runs)
        queue_ms = sum(r.queue_ms or 0 for r in runs)
        all_calls = [c for rid in by_run for c in by_run[rid]] + outside
        given = sum(t.budget for t in chain) + sum(m.budget for m in msgs.values() if m.sender == ROOT and m.type == "note"
                                                   and m.to in members and in_windows(m.id))
        per_task: list[JsonObject] = []
        for (step_task, step_result), (a, b) in zip(steps, windows):
            mine_runs = [x for x in runs if in_window(x.run.rpartition("@")[2], a, b)]
            per_task.append({"task": step_task.id, "title": step_task.title, "state": step_result.status if step_result is not None else "open",
                             "runs": len(mine_runs), "budget": step_task.budget})
        returned = sum(r.budget for _, r in steps if r is not None and r.status in ("done", "failed"))
        totals: JsonObject = {
            "wall_ms": max(0.0, ms_between(t0, t_end)), "runs": len(runs), "run_ms": run_ms, "queue_ms": queue_ms,
            "user_wait_ms": user_ms, "tool_calls": len(all_calls),
            "refusals": sum(1 for c in all_calls if c.get("ok") is False),
            "outcomes": dict(Counter(r.outcome for r in runs)),
            "budget_given": given, "budget_used": len(runs), "budget_returned": returned, "tasks": per_task,
        }
        shown = [cast(JsonObject, plain(i)) | {"rel_ms": max(0.0, ms_between(t0, cast(datetime, i["t"])))} for i in items]
        return {"task": tid, "title": task.title, "assignee": task.to, "state": state, "partial": any(n != redirect for n in notes),
                "notes": notes, "start": iso(t0), "end": iso(t_end) if final else None, "team": team,
                "window": {"start": start21, "end": end21}, "items": shown, "totals": totals}
