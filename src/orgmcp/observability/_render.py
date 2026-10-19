"""The text of the views: compact lines for a terminal or a model, from the JSON the queries answer."""

from __future__ import annotations

from typing import Any

from ..kernel import clip_line, depth, fmt_dur
from ._pure import fmt_rel, format_event
from ._util import cap
from .api import ObservabilityRenderer


class TextObservabilityRenderer(ObservabilityRenderer):
    """Renders the views as lines of text; it holds nothing, so one serves every view. The views are JSON read key by key (``dict[str, Any]``: a view is
    what the queries answered, however it came to be)."""

    def render_events(self, view: dict[str, Any], max_lines: int | None = None) -> str:
        evs = view["events"]
        if not evs:
            return "(no matching events)" + ("" if view.get("any", True) else " - this organization has no event files yet")
        lines = [format_event(ev) for ev in evs]
        head = f"{view['shown']} of {view['total']} matching event(s), oldest first"
        if view["total"] > view["shown"]:
            head += f" - {view['total'] - view['shown']} earlier one(s) not shown: narrow with since/agent/kind/trace or raise the limit"
        return "\n".join([head, *cap(lines, max_lines, "since/agent/kind/trace")])

    def render_trace(self, tr: dict[str, Any], max_lines: int | None = None) -> str:
        t = tr["totals"]
        head = f'trace {tr["task"]} "{tr["title"]}" -> {tr["assignee"]}: {tr["state"]}' + ("  [partial]" if tr["partial"] else "")
        lines: list[str] = []
        for it in tr["items"]:
            pad = "  " * depth(it["agent"]) if it.get("agent") else ""
            rel = f'{fmt_rel(it["rel_ms"]):>8}  '
            k = it["kind"]
            if k == "message":
                mark = "" if it["trace_source"] == "recorded" else "~"
                text = f'{it["from"]} -> {it["to"]} {it["type"]}' + (f' ({it["status"]})' if it.get("status") else "")
                text += f' "{clip_line(it["title"], 60)}"' if it.get("title") else ""
                text += f' +{it["budget"]} run(s)' if it.get("budget") else ""
                lines.append(f"{rel}{pad}{mark}{text}")
            elif k == "run":
                calls = it["tool_calls"]
                bits = [it["outcome"]]
                if it.get("duration_ms") is not None:
                    bits.append(f'ran {fmt_dur(it["duration_ms"])}')
                if it.get("queue_ms") is not None:
                    bits.append(f'queued {fmt_dur(it["queue_ms"])}')
                if it["source"] == "events":
                    tools = " ".join(f"{n}×{c}" for n, c in sorted(calls["by_tool"].items(), key=lambda kv: (-kv[1], kv[0])))
                    bits.append(f'{calls["total"]} call(s)' + (f" [{tools}]" if tools else "")
                                + (f', {len(calls["refused"])} refused' if calls["refused"] else ""))
                if it.get("shared_with"):
                    bits.append(f"shared with {len(it['shared_with'])} other request(s)")
                if it.get("error"):
                    bits.append(f'error: {clip_line(it["error"], 120)}')
                lines.append(f'{rel}{pad}run {it["run"].split("@", 1)[-1]} {", ".join(bits)}')
                for r in calls["refused"]:
                    lines.append(f'{"":>10}{pad}  ! {r["tool"]}: {clip_line(r["error"], 200)}')
            elif k == "tool":
                ok = "ok" if it.get("ok") else f'REFUSED: {clip_line(it.get("error") or "", 200)}'
                lines.append(f'{rel}{pad}{it["agent"]} {it["tool"]} {ok}')
            else:
                d = it["detail"]
                lines.append(f'{rel}{pad}* {it["event"]} {clip_line(" ".join(f"{a}={b}" for a, b in d.items() if b not in (None, "")), 160)}')
        foot = (f'totals: wall {fmt_dur(t["wall_ms"])} | runs {t["runs"]} (budget given {t["budget_given"]}, '
                f'returned {t["budget_returned"]}) | run time {fmt_dur(t["run_ms"])} | queue {fmt_dur(t["queue_ms"])} | '
                f'waiting on you {fmt_dur(t["user_wait_ms"])} | tool calls {t["tool_calls"]} ({t["refusals"]} refused)')
        out = [head, *cap(lines, max_lines, f"observe events --trace {tr['task']} (agent=/kind=/errors)")]
        if len(t.get("tasks") or ()) > 1:  # reworks: each task's runs are what `progress` reports for it
            out.append("tasks: " + " | ".join(f'{x["task"]} "{clip_line(x["title"], 30)}" {x["state"]} {x["runs"]} run(s)' for x in t["tasks"]))
        out.append(foot)
        out += [f"note: {n}" for n in tr["notes"]]
        return "\n".join(out)

    def render_metrics(self, m: dict[str, Any], limit: int = 50) -> str:
        r, tc = m["runs"], m["tool_calls"]
        lines = [f'metrics {m["since"][:19]}Z .. {m["until"][:19]}Z' + (f' agent={m["agent"]}' if m.get("agent") else "")
                 + f' ({m["events"]} event(s) in the window)']
        d, q = r["duration_ms"], r["queue_ms"]
        lines.append(f'runs {r["total"]}: ok {r["ok"]}, failed {r["failed"]}, timeout {r["timeout"]}, killed {r["killed"]}'
                     + (f', running {r["running"]}' if r["running"] else "") + (f', unknown {r["unknown"]}' if r["unknown"] else "")
                     + f' | duration p50 {fmt_dur(d["p50"])} p95 {fmt_dur(d["p95"])} max {fmt_dur(d["max"])} (n={d["n"]})'
                     + f' | queue p50 {fmt_dur(q["p50"])} p95 {fmt_dur(q["p95"])} (n={q["n"]})')
        lines.append(f'budget spent {m["budget_spent"]} run(s)')
        lines.append(f'tool calls {tc["total"]}, refused {tc["refused"]} ({tc["refusal_rate"]:.1%})')
        for name, t in sorted(tc["by_tool"].items(), key=lambda kv: (-kv[1]["calls"], kv[0]))[:limit]:
            lines.append(f'  {name:<16} {t["calls"]:>5} calls {t["refused"]:>3} refused ({t["refusal_rate"]:.0%})'
                         f' p50 {fmt_dur(t["ms"]["p50"])} p95 {fmt_dur(t["ms"]["p95"])}'
                         + (f' [{t["exceptions"]} exception(s)]' if t["exceptions"] else ""))
        if m["top_refusals"]:
            lines.append("top refusals:")
            lines += [f'  {x["count"]}x {x["message"]}  ({", ".join(f"{k}x{v}" for k, v in x["tools"].items())})' for x in m["top_refusals"]]
        lines.append("messages: " + (", ".join(f"{k} {v}" for k, v in sorted(m["messages"].items())) or "none"))
        s = m["scheduler"]
        lines.append(f'scheduler: {s["starts"]} start(s); errors: ' + (", ".join(f"{k} x{v}" for k, v in s["errors"].items()) or "none")
                     + "; exits: " + (", ".join(f"{k} x{v}" for k, v in s["exits"].items()) or "none"))
        lines.append(f'stalls {m["stalls"]}, pauses {m["pauses"]["total"]}'
                     + (f' ({", ".join(f"{k} x{v}" for k, v in m["pauses"]["by_reason"].items())})' if m["pauses"]["total"] else "")
                     + f', agent failures {m["agent_failures"]}, orphaned runs {m["orphans"]}')
        if m.get("by"):
            b = m["by"]
            lines.append(f'by {b["dimension"]}:')
            rows = b["rows"]
            for x in rows[:limit]:
                runs_part = (f'runs {x["runs"]:>3} (ok {x["ok"]}, bad {x["failed"]}) run p50 {fmt_dur(x["run_ms"]["p50"])}'
                             f' p95 {fmt_dur(x["run_ms"]["p95"])} | ') if b["dimension"] != "tool" else ""
                calls_part = (f'calls {x["calls"]:>4} refused {x["refused"]} ({x["refusal_rate"]:.0%})'
                              f' p50 {fmt_dur(x["call_ms"]["p50"])} p95 {fmt_dur(x["call_ms"]["p95"])}')
                lines.append(f'  {clip_line(x["key"], 48):<48} {runs_part}{calls_part}')
            if len(rows) > limit:
                lines.append(f"... {len(rows) - limit} more row(s), narrow with since/agent")
        if not m["events"]:
            lines.append("(no events in this window: run counts come from the run logs; tool calls and queue waits need events)")
        return "\n".join(lines)

    def render_now(self, v: dict[str, Any], max_lines: int | None = None) -> str:
        s = v["scheduler"]
        if s["state"] == "running":
            bits = [b for b in (s.get("mode"), f'up {fmt_dur(s["uptime_s"] * 1000)}' if s.get("uptime_s") is not None else None) if b]
            if s.get("last_heartbeat_age_s") is not None:
                bits.append(f'last heartbeat {fmt_dur(s["last_heartbeat_age_s"] * 1000)} ago')
            elif s.get("uptime_s") is not None:
                bits.append("no heartbeat seen")
            line = f'scheduler: running pid {s["pid"]}' + (f' ({", ".join(bits)})' if bits else "")
        elif s["state"] == "unverified":
            line = f'scheduler: unverified - pid file names pid {s["pid"]} ({s["detail"]})'
        else:
            line = "scheduler: stopped" + (f' (last exit: {s["last_exit"]})' if s.get("last_exit") else "")
        lines = [line, f'runs in flight {len(v["runs_in_flight"])}/{v["max_parallel"]}' + (":" if v["runs_in_flight"] else "")]
        for r in v["runs_in_flight"]:
            lines.append(f'  {r["agent"]} {fmt_dur((r["elapsed_s"] or 0) * 1000)} {clip_line(", ".join(r["batch"]), 80)}'
                         + (f' trace {", ".join(r["traces"])}' if r["traces"] else ""))
        if v["queued"]:
            lines.append(f'queued, not running ({len(v["queued"])}):')
            for q in v["queued"]:
                lines.append(f'  {q["agent"]}: {q["unread"]} unread' + (f', oldest {fmt_dur(q["waiting_s"] * 1000)}' if q["waiting_s"] is not None else "")
                             + f' - {q["reason"]}')
        else:
            lines.append("queued, not running: none")
        if v["waiting_on_you"]:
            lines.append(f'waiting on you ({len(v["waiting_on_you"])}):')
            lines += [f"  {x}" for x in v["waiting_on_you"]]
        else:
            lines.append("waiting on you: nothing")
        e = v["errors_15m"]
        lines.append(f'errors in the last 15 min: {e["count"]}' + ("" if v["events_seen"] else " (no events recorded in this organization)"))
        lines += [f"  {format_event(ev, 200)}" for ev in e["events"]]
        if v["paused"]:
            lines.append("paused: " + ", ".join(f"{a} ({r})" for a, r in v["paused"].items()))
        return "\n".join(cap(lines, max_lines, "observe events errors_only=true"))

    def render_check(self, res: dict[str, Any]) -> str:
        lines = []
        for c in res["checks"]:
            lines.append(f'({c["id"]}) {"PASS" if c["ok"] else "FAIL"} {c["name"]}')
            lines += [f"      {d}" for d in c["details"]]
        bad = [c["id"] for c in res["checks"] if not c["ok"]]
        lines.append("all checks passed" if not bad else f'FAILED: {", ".join(bad)}')
        return "\n".join(lines)
