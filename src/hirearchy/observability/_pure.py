"""The vocabulary of the views, as pure functions: ranks, times, refusals, what an error is, one line of an event."""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from typing import cast

from ..eventlog import ENVELOPE as _ENVELOPE
from ..kernel import JsonObject, OrgError, aware, clip_line, fmt_dur, parse_time

ENVELOPE = set(_ENVELOPE)


def fmt_rel(ms: float) -> str:
    """Time relative to the start of a request: ``+0s``, ``+42s``, ``+1m05s``, ``+2h03m``."""
    s = int(max(0.0, ms) // 1000)
    if s < 60:
        return f"+{s}s"
    if s < 3600:
        return f"+{s // 60}m{s % 60:02d}s"
    return f"+{s // 3600}h{(s % 3600) // 60:02d}m"


def percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile: the ``ceil(p/100 * n)``-th smallest value (exact, no interpolation); None if empty."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
_SPAN = re.compile(r"(\d+(?:\.\d+)?)\s*([smhdw])")


def parse_when(text: str | datetime | None, now: datetime | None = None) -> datetime | None:
    """A point in time from ``15m`` / ``24h`` / ``7d`` (that long before ``now``), ``now``, or an ISO timestamp
    (a naive one is UTC). None for None or an empty string. Without ``now`` the wall clock is the time."""
    if text is None or text == "":
        return None
    if isinstance(text, datetime):
        return aware(text)
    now = aware(now) if now is not None else datetime.now(timezone.utc)
    raw = str(text).strip()
    m = _SPAN.fullmatch(raw.lower())
    if m:
        return now - timedelta(seconds=float(m.group(1)) * _UNITS[m.group(2)])
    if raw.lower() == "now":
        return now
    try:
        return aware(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    except ValueError:
        raise OrgError(f"cannot read {raw!r} as a time: use a duration like 15m, 24h, 7d or an ISO timestamp "
                       "like 2026-10-18T10:00:00Z") from None


_ID = re.compile(r"\b\d{8}T\d{6,}[\w.-]*")
_PATH = re.compile(r"(?<![\w.])(?:/[\w.@+~-]+){2,}/?|(?<![\w/])[\w.-]+(?:/[\w.-]+)*\.\w{1,6}\b")
_QUOTED = re.compile(r'"[^"]*"|\'[^\']*\'')
_HEX = re.compile(r"\b[0-9a-f]{8,}\b")
_NUM = re.compile(r"\b\d+\b")


def normalize_refusal(text: str) -> str:
    """A refusal text with what varies removed (message ids, paths, quoted titles, hashes, numbers), so identical
    reasons group together."""
    t = _ID.sub("<id>", str(text))
    t = _QUOTED.sub("<text>", t)
    t = _PATH.sub("<path>", t)
    t = _HEX.sub("<hex>", t)
    t = _NUM.sub("N", t)
    return clip_line(t, 160)


def is_error(ev: JsonObject) -> bool:
    """Events that mean something went wrong: a refused or failed tool call, a failed command, a run that did not end
    cleanly, a scheduler phase that raised, an orphaned run, an agent failure."""
    kind = ev.get("kind")
    if kind in ("tool.call", "cli.command"):
        return ev.get("ok") is False
    if kind == "run.end":
        return ev.get("ok") is False or bool(ev.get("timed_out") or ev.get("killed"))
    return kind in ("scheduler.error", "run.orphan", "agent.failure")


def format_event(ev: JsonObject, width: int = 300) -> str:
    """One line: time, process, actor, kind, then the interesting fields."""
    t = parse_time(ev.get("ts"))
    clock = (t.strftime("%H:%M:%S") + (f".{t.microsecond // 1000:03d}" if t.microsecond else "")) if t else str(ev.get("ts", ""))[:12]
    kind = str(ev.get("kind", "?"))
    parts = [f"{clock} {str(ev.get('proc', '?')):<9} {str(ev.get('actor') or '-'):<14} {kind}"]
    if kind == "tool.call":
        parts.append(f"{ev.get('tool')} {'ok' if ev.get('ok') else 'REFUSED' if ev.get('error_type') in (None, 'OrgError') else 'FAILED'}"
                     f" {fmt_dur(cast('float | None', ev.get('ms')))}")
    elif kind == "run.end":
        parts.append(f"{'ok' if ev.get('ok') else 'FAILED'} {fmt_dur(cast('float | None', ev.get('duration_ms')))}"
                     + (" timed-out" if ev.get("timed_out") else "") + (" killed" if ev.get("killed") else ""))
    for key, value in ev.items():
        if key in ENVELOPE or key in ("tool", "ms", "duration_ms") or (kind == "tool.call" and key == "ok"):
            continue
        if kind == "run.end" and key in ("ok", "timed_out", "killed"):
            continue
        if value in (None, "", [], {}):
            continue
        if isinstance(value, dict):
            value = ",".join(f"{k}={v}" for k, v in value.items())
        elif isinstance(value, list):
            value = ",".join(str(v) for v in value)
        parts.append(f"{key}={value}" if key != "error" else f'error="{value}"')
    if ev.get("run"):
        parts.append(f"run={ev['run']}")
    if ev.get("trace"):
        parts.append(f"trace={ev['trace']}")
    return clip_line(" ".join(parts), width)

