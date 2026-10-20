"""Runtime fields of ``eventlog`` (ARCHITECTURE.md 3.6): one field per port that ``wire_eventlog.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..eventlog import EventFollowers, EventReader

STEP: str | None = "A-eventlog"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {
    "EventFollower": "a value that EventFollowers.follow returns for each tail (it has its own position), not a port built once",
}


@dataclass(frozen=True)
class Fields:
    event_reader: EventReader
    event_followers: EventFollowers
