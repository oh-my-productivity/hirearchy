"""The legacy time helpers of ``orgmcp.health``, frozen verbatim from commit ``bdfb82a`` (``r1-integration``).

``health._aware _parse_time _stamp _msg_time _duration`` became aliases of the kernel's functions in step K1, and ``observe.fmt_dur`` and
``observe._clip`` / ``services._clip`` followed; the live legacy names can no longer serve as the oracle for them (they are gone, or the same objects);
these copies do.
"""

from __future__ import annotations

from datetime import datetime, timezone

from orgmcp.kernel import Message

_STAMP = "%Y%m%dT%H%M%S%f"


def _aware(t: datetime | None) -> datetime | None:
    return t if t is None or t.tzinfo else t.replace(tzinfo=timezone.utc)


def _parse_time(value: object) -> datetime | None:
    """Accept the ISO strings (or YAML-parsed datetimes) stored in message and charter frontmatter."""
    if isinstance(value, datetime):
        return _aware(value)
    try:
        return _aware(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


def _stamp(name: str) -> datetime | None:
    try:
        return datetime.strptime(name[:21], _STAMP).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _msg_time(m: Message) -> datetime | None:
    """When a message was sent: the microsecond timestamp in its id, else its ``created`` second."""
    return _stamp(m.id) or _parse_time(m.created)


def _duration(seconds: float | None) -> str:
    s = int(seconds or 0)
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if s >= size:
            return f"{s // size}{unit}"
    return f"{s}s"


def _fmt_dur(ms: float | None) -> str:
    """A duration: ``850ms``, ``4.2s``, ``42s``, ``1m05s``, ``2h03m`` (``observe.fmt_dur``)."""
    if ms is None:
        return "?"
    ms = max(0.0, float(ms))
    if ms == 0:
        return "0s"
    if ms < 1000:
        return f"{ms:.0f}ms"
    s = ms / 1000
    if s < 10:
        return f"{s:.1f}s"
    s = int(round(s))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m{s % 60:02d}s"
    return f"{s // 3600}h{(s % 3600) // 60:02d}m"


def _clip(text: object, limit: int) -> str:
    """``observe._clip`` and ``services._clip`` (two identical copies)."""
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
