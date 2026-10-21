"""``plain``: a value as JSON-able data (datetimes as ISO strings).

Not the same function as ``observability``'s: that one also turns tuples, sets and paths into JSON and normalises times to UTC, which
would change the output of ``health --json``; the two stay separate on purpose (ARCHITECTURE.md 10.4, item 5).
"""

from __future__ import annotations

from datetime import datetime


def plain(value: object) -> object:
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [plain(v) for v in value]
    return value.isoformat() if isinstance(value, datetime) else value
