"""The legacy time helpers of ``orgmcp.health``, frozen verbatim from commit ``bdfb82a`` (``r1-integration``).

``health._aware _parse_time _stamp _msg_time _duration`` become aliases of the kernel's functions in step K1, so the
live legacy names can no longer serve as the oracle for them; these copies do. (``observe.fmt_dur`` is still a separate
legacy implementation and is compared live.) Delete this module together with ``test_timeutil.py``'s oracle tests when the
last legacy duplicate is gone (step E1).
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
