"""Builders of the records the ledger tests append (no test lives here)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hirearchy.retro import BriefRecord, RecordedItem

ORIGIN = datetime(2026, 11, 2, 9, 40, 5, tzinfo=timezone.utc)


def record(n: int, *keys: str, lapsed: int = 0) -> BriefRecord:
    """The brief ``B<n>``, held ``n`` days after the origin, offering one item for each of ``keys``."""
    items = tuple(
        RecordedItem(i, "service", key, (f"E{n}-{i}",), {"service": f"lead/{key}"}, lapsed) for i, key in enumerate(keys, start=1)
    )
    return BriefRecord(f"B{n}", ORIGIN + timedelta(days=n), ORIGIN + timedelta(days=n - 1) if n > 1 else None, "mcp", items, (f"held|{n}",))
