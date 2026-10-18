"""Events for a human: one readable line per event (``orgmcp dash`` Activity tab, Overview, Events screen, Health).

``observe.format_event`` prints an event the way the log has it (ids, pgids, budgets before/after, argument summaries):
exact, but a wall of ``key=value``. :func:`humanize` says what happened::

    10:05:27 run started (batch: note "Scope change" from root)
    10:05:30 inbox ok 5ms
    10:05:40 delegate → ceo/analyst REFUSED: not enough budget: you have 5 run(s) and must keep 2 in reserve
    10:06:00 run ended ok after 33s
    10:06:01 sent result (done) "Quarterly market report" → root

Ids, process groups and the like are left out; the raw form (``observe.format_event``) stays one key away in the UI.
Pure functions, no I/O: message titles of a run's batch come from the ``lookup`` callable the caller passes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import observe
from .observe import fmt_dur

WHO_WIDTH = 14
BATCH_SHOWN = 3

# (agent, message id) -> (type, title, sender) of a message, or None when it cannot be found
Lookup = Callable[[str, str], "tuple[str, str, str] | None"]


@dataclass
class EventLine:
    text: str  # the whole line
    error: bool  # refused / failed: shown as an error

    def __str__(self) -> str:  # pragma: no cover - debugging aid
        return self.text


def clock(ev: dict) -> str:
    t = observe._ts(ev.get("ts"))
    return t.strftime("%H:%M:%S") if t else str(ev.get("ts", ""))[:8]


def who(ev: dict) -> str:
    """The agent / process an event is about (the 'who' column of the merged stream)."""
    kind = str(ev.get("kind", ""))
    if kind.startswith(("scheduler.", "prune")):
        return "scheduler"
    if kind.startswith(("run.", "agent.failure", "stall.")) and ev.get("agent"):
        return str(ev["agent"])
    return str(ev.get("actor") or ev.get("agent") or "-")


def _msg_phrase(msg: tuple[str, str, str]) -> str:
    typ, title, sender = msg
    return f'{typ} "{observe._clip(title, 60)}" from {sender}' if title else f"{typ} from {sender}"


def _batch(ev: dict, lookup: Lookup | None) -> str:
    ids = [str(i) for i in (ev.get("batch") or [])]
    agent = str(ev.get("agent") or ev.get("actor") or "")
    found = [m for m in (lookup(agent, i) for i in ids[:BATCH_SHOWN]) if m] if lookup and agent else []
    if not ids:
        return ""
    if not found:
        return f"batch of {len(ids)} message(s)"
    text = "batch: " + ", ".join(_msg_phrase(m) for m in found)
    rest = len(ids) - len(found)
    return text + (f", +{rest} more" if rest > 0 else "")


def _runs(n) -> str:
    return f"+{n} run(s)" if isinstance(n, (int, float)) and not isinstance(n, bool) and n > 0 else ""


def _tool_detail(args: dict, budget: bool = True) -> str:
    """The arguments of a tool call that mean something to a human (ids and bodies are left to the raw form)."""
    if not isinstance(args, dict):
        return ""
    bits: list[str] = []
    if args.get("to"):
        bits.append(f"→ {args['to']}")
    for key in ("agent", "owner", "name", "service", "path", "target", "view"):
        if args.get(key):
            bits.append(str(args[key]))
    if args.get("title"):
        bits.append(f'"{observe._clip(args["title"], 60)}"')
    if args.get("status"):
        bits.append(f"({args['status']})")
    if args.get("verdict"):
        bits.append(str(args["verdict"]))
    if budget and _runs(args.get("budget")):
        bits.append(_runs(args["budget"]))
    return " ".join(bits)


def _error_text(ev: dict) -> str:
    err = str(ev.get("error") or "").strip()
    return err or str(ev.get("error_type") or "")


def describe(ev: dict, me: str | None = None, lookup: Lookup | None = None) -> str:
    """What happened, without time and without the 'who'. ``me``: the agent whose view this is (a message to ``me``
    reads 'received ... from X', one from ``me`` 'sent ... → X')."""
    kind = str(ev.get("kind", "?"))
    if kind == "tool.call":
        tool = str(ev.get("tool") or "?")
        detail = _tool_detail(ev.get("args") or {}, budget=bool(ev.get("ok")))  # a refusal says why itself
        head = f"{tool} {detail}".strip()
        if ev.get("ok"):
            return f"{head} ok {fmt_dur(ev.get('ms'))}"
        refused = ev.get("error_type") in (None, "OrgError")
        err = _error_text(ev)
        return f"{head} {'REFUSED' if refused else 'FAILED'}" + (f": {err}" if err else "")
    if kind == "cli.command":
        head = f"command `orgmcp {ev.get('command', '?')}`"
        if ev.get("ok"):
            return f"{head} ok {fmt_dur(ev.get('ms'))}"
        err = _error_text(ev)
        return f"{head} FAILED" + (f": {err}" if err else "")
    if kind == "run.start":
        batch = _batch(ev, lookup)
        return "run started" + (f" ({batch})" if batch else "")
    if kind == "run.end":
        after = f" after {fmt_dur(ev.get('duration_ms'))}" if ev.get("duration_ms") is not None else ""
        if ev.get("ok") and not (ev.get("timed_out") or ev.get("killed")):
            return f"run ended ok{after}"
        why = "timed out" if ev.get("timed_out") else "killed" if ev.get("killed") else _error_text(ev)
        return f"run ended FAILED{after}" + (f": {why}" if why else "")
    if kind == "run.orphan":
        detail = str(ev.get("detail") or "")
        return f"orphaned run {ev.get('action', '?')}" + (f": {detail}" if detail else "")
    if kind == "msg.deliver":
        typ = str(ev.get("type") or "message")
        status = f" ({ev['status']})" if ev.get("status") else ""
        title = f' "{observe._clip(ev["title"], 70)}"' if ev.get("title") else ""
        extra = (" " + _runs(ev.get("budget"))) if _runs(ev.get("budget")) else ""
        sender, to = str(ev.get("from") or ev.get("actor") or "?"), str(ev.get("to") or "?")
        if me is not None and to == me and sender != me:
            return f"received {typ}{status}{title} from {sender}{extra}"
        text = f"sent {typ}{status}{title} → {to}{extra}"
        if ev.get("feedback"):
            text += f" [feedback: {ev['feedback']}]"
        return text
    if kind == "agent.failure":
        return f"run failed: {ev.get('count', '?')} consecutive failed run(s)"
    if kind == "agent.pause":
        return f"paused{': ' + str(ev['reason']) if ev.get('reason') else ''}"
    if kind == "agent.resume":
        return f"resumed{': ' + str(ev['reason']) if ev.get('reason') else ''}"
    if kind == "agent.hire":
        return f"hired {ev.get('agent', '?')}" + (f" ({ev['role']})" if ev.get("role") else "")
    if kind == "agent.retire":
        return f"retired {ev.get('agent', '?')}" + (f": {ev['reason']}" if ev.get("reason") else "")
    if kind in ("service.define", "service.revise", "service.retire"):
        verb = kind.split(".", 1)[1]
        v = f" v{ev['version']}" if ev.get("version") else ""
        return f"service {ev.get('owner', '?')}/{ev.get('service', '?')}{v} {verb}d"
    if kind == "scheduler.start":
        return f"scheduler started ({ev.get('mode', '?')}, max_parallel {ev.get('max_parallel', '?')})"
    if kind == "scheduler.exit":
        return f"scheduler exited: {ev.get('reason', '?')}"
    if kind == "scheduler.heartbeat":
        running = ev.get("running") or []
        return (f"scheduler heartbeat: {len(running) if isinstance(running, list) else running} running, "
                f"{ev.get('runnable', 0)} runnable, {ev.get('waiting_on_you', 0)} waiting on you")
    if kind == "scheduler.error":
        return f"scheduler error in {ev.get('phase', '?')}: {ev.get('error', '?')}"
    if kind == "stall.nudge":
        return f"stall nudge → {ev.get('to', '?')} (step {ev.get('step', '?')})"
    if kind == "prune":
        days = ev.get("removed_days")
        return f"pruned {len(days) if isinstance(days, (list, tuple)) else days or 0} old day(s) of events"
    if kind == "review.run":
        return f"review run: {ev.get('flagged', 0)} flagged"
    skip = observe.ENVELOPE | {"agent"}
    rest = " ".join(f"{k}={v}" for k, v in ev.items() if k not in skip and v not in (None, "", [], {}))
    return f"{kind} {rest}".strip()


def humanize(ev: dict, me: str | None = None, actor: bool = False, lookup: Lookup | None = None,
             width: int | None = None) -> EventLine:
    """One readable line. ``actor``: put who it is about in front (the merged stream); ``me``: the view of one agent."""
    text = f"{clock(ev)} "
    if actor:
        text += f"{observe._clip(who(ev), WHO_WIDTH):<{WHO_WIDTH}} "
    text += describe(ev, me, lookup)
    if width is not None and len(text) > width:
        text = text[: width - 1].rstrip() + "…"
    return EventLine(text, observe.is_error(ev))


def event_lines(events: list[dict], me: str | None = None, actor: bool = False, raw: bool = False,
                lookup: Lookup | None = None, raw_width: int = 600) -> list[EventLine]:
    """Every event as a line: readable, or (``raw``) exactly as the log has it."""
    if raw:
        return [EventLine(observe.format_event(ev, raw_width), observe.is_error(ev)) for ev in events]
    return [humanize(ev, me=me, actor=actor, lookup=lookup) for ev in events]
