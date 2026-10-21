"""Small helpers of the views: times as text, differences, statistics, JSON-able copies, capped lists, event matchers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from ..kernel import JsonObject, norm
from ._pure import is_error, percentile


def iso(t: datetime | None) -> str | None:
    return t.astimezone(timezone.utc).isoformat() if t else None


def ms_between(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() * 1000


def stats(values: Sequence[float]) -> JsonObject:
    return {"n": len(values), "p50": percentile(list(values), 50), "p95": percentile(list(values), 95),
            "max": max(values) if values else None}


def plain(value: object) -> object:
    """JSON-able copy: datetimes as ISO strings, tuples/sets as lists, Paths as strings."""
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [plain(v) for v in value]
    if isinstance(value, datetime):
        return iso(value)
    if isinstance(value, Path):
        return str(value)
    return value


def cap(lines: list[str], max_lines: int | None, hint: str) -> list[str]:
    if max_lines is None or len(lines) <= max_lines:
        return lines
    return lines[:max_lines] + [f"... {len(lines) - max_lines} more line(s), narrow with {hint}"]


def matcher(agent: str | None = None, kind: str | None = None, trace: str | None = None, errors: bool = False) -> Callable[[JsonObject], bool]:
    """Which events a filter lets through: ``kind`` is the kind or its prefix, ``agent`` the actor, the agent or an end of the message,
    ``trace`` the trace or one of the traces, ``errors`` only what ``is_error`` says."""
    agent = norm(agent) if agent else None
    kind = kind.rstrip("*").rstrip(".") if kind else None

    def match(ev: JsonObject) -> bool:
        if kind:
            k = str(ev.get("kind", ""))
            if k != kind and not k.startswith(kind + "."):
                return False
        if agent and agent not in (ev.get("actor"), ev.get("agent"), ev.get("from"), ev.get("to")):
            return False
        if trace and trace != ev.get("trace") and trace not in cast("Sequence[object]", ev.get("traces") or ()):
            return False
        return not errors or is_error(ev)

    return match
