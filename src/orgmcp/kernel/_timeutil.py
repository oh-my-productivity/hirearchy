"""Time vocabulary: aware datetimes, the timestamps in ids and file names, durations as text."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import overload

from ._message import Message

STAMP_FORMAT = "%Y%m%dT%H%M%S%f"  # prefix of message ids and run log names


@overload
def aware(t: datetime) -> datetime: ...
@overload
def aware(t: None) -> None: ...
@overload
def aware(t: datetime | None) -> datetime | None: ...
def aware(t: datetime | None) -> datetime | None:
    """``t`` with UTC attached when it has no time zone."""
    return t if t is None or t.tzinfo else t.replace(tzinfo=timezone.utc)


def parse_time(value: object) -> datetime | None:
    """An aware datetime from the ISO strings (or YAML-parsed datetimes) in frontmatter; None when unreadable."""
    if isinstance(value, datetime):
        return aware(value)
    try:
        return aware(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


def stamp_of(name: str) -> datetime | None:
    """The time in the first 21 characters of an id or log file name; None when there is none."""
    try:
        return datetime.strptime(name[:21], STAMP_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def msg_time(m: Message) -> datetime | None:
    """When a message was sent: the microsecond timestamp in its id, else its ``created`` second."""
    return stamp_of(m.id) or parse_time(m.created)


def fmt_duration(seconds: float | None) -> str:
    """A coarse duration: ``45s``, ``7m``, ``3h``, ``2d``."""
    s = int(seconds or 0)
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if s >= size:
            return f"{s // size}{unit}"
    return f"{s}s"


def fmt_dur(ms: float | None) -> str:
    """A duration given in milliseconds: ``850ms``, ``4.2s``, ``42s``, ``1m05s``, ``2h03m``."""
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
