"""What every invariant answers with, and the thresholds they share."""

from __future__ import annotations

from typing import SupportsInt, cast

from ...kernel import JsonObject
from ...mail import MessageFile

COPY_GRACE = 5.0  # seconds a freshly written message may lack its other copy (delivery writes two files)
INFLIGHT_GRACE = 30.0  # seconds an inflight batch may exist before the run record is written
RECV_BOXES = ("inbox", "inflight", "read")


def verdict(cid: str, name: str, problems: list[str], note: str = "", limit: int = 8) -> JsonObject:
    """``{"id", "name", "ok", "details"}``: the first ``limit`` problems and how many more there are, else the note."""
    details = problems[:limit] + ([f"... and {len(problems) - limit} more"] if len(problems) > limit else [])
    return {"id": cid, "name": name, "ok": not problems, "details": details or ([note] if note else [])}


def runs_of(f: MessageFile) -> int:
    """The runs of budget a message carries (its ``budget``)."""
    return int(cast("SupportsInt | str", (f.meta or {}).get("budget") or 0))
