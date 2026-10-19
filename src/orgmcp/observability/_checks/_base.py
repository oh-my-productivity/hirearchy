"""What every invariant answers with, and the thresholds they share."""

from __future__ import annotations

from ...kernel import JsonObject

COPY_GRACE = 5.0  # seconds a freshly written message may lack its other copy (delivery writes two files)
INFLIGHT_GRACE = 30.0  # seconds an inflight batch may exist before the run record is written
RECV_BOXES = ("inbox", "inflight", "read")


def verdict(cid: str, name: str, problems: list[str], note: str = "", limit: int = 8) -> JsonObject:
    """(RED: skeleton.)"""
    raise NotImplementedError("red: C-obs-2")
