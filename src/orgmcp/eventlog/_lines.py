"""The lines of an event file and the days of a window: the rules of the format that need no file (pure functions)."""

from __future__ import annotations

import heapq
import json
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from typing import cast

from ..kernel import JsonObject, parse_time
from .api import DAY_RE


def event_of(raw: bytes) -> JsonObject | None:
    """The JSON object on a line; None for anything else (a partial line, text, a number, a list)."""
    try:
        ev = json.loads(raw)
    except ValueError:
        return None
    return cast(JsonObject, ev) if isinstance(ev, dict) else None


def timed_of(lines: Iterable[bytes]) -> Iterator[tuple[datetime, JsonObject]]:
    """(time, event) of every line that is an event with a readable ``ts``."""
    for raw in lines:
        ev = event_of(raw)
        if ev is None:
            continue
        t = parse_time(ev.get("ts"))
        if t is not None:
            yield t, ev


def merged(
    streams: list[Iterator[tuple[datetime, JsonObject]]], since: datetime | None, until: datetime | None
) -> Iterator[tuple[datetime, JsonObject]]:
    """The streams as one in time order (a heap merge: every file is time-ordered by its single writer), cut to ``[since, until]``."""
    for t, ev in heapq.merge(*streams, key=lambda item: item[0]):
        if since is not None and t < since:
            continue
        if until is not None and t > until:
            continue
        yield t, ev


def tail_of(data: bytes, size: int, nbytes: int) -> list[JsonObject]:
    """The events on the last ``nbytes`` bytes of a file of ``size`` bytes; ``data`` is those bytes. The first line is dropped when the
    cut is inside the file, since it is cut."""
    lines = data.splitlines()
    if size > nbytes and lines:
        lines = lines[1:]  # the first line is cut
    return [ev for ev in map(event_of, lines) if ev is not None]


def new_events(data: bytes) -> tuple[int, list[tuple[datetime, JsonObject]]]:
    """(bytes consumed, events) of newly appended ``data``: only the complete lines, so 0 and nothing while the last line is partial."""
    end = data.rfind(b"\n")
    if end < 0:
        return 0, []  # no complete line yet
    return end + 1, list(timed_of(data[: end + 1].splitlines()))


def days_of(names: Iterable[str], since: datetime | None, until: datetime | None) -> list[str]:
    """The day directories among ``names`` (``YYYY-MM-DD``) that the UTC days of ``[since, until]`` cover, in order."""
    lo = since.astimezone(timezone.utc).date().isoformat() if since else None
    hi = until.astimezone(timezone.utc).date().isoformat() if until else None
    return [n for n in sorted(n for n in names if DAY_RE.fullmatch(n)) if (lo is None or n >= lo) and (hi is None or n <= hi)]


def is_event_name(name: str) -> bool:
    """A file name that can hold events: ``*.jsonl``, not hidden."""
    return name.endswith(".jsonl") and not name.startswith(".")
