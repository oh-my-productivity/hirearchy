"""``parse_since``: the ``since`` of ``retro()`` and of ``hirearchy retro --since`` (design 14.2; pure): a date, a datetime with an offset or a message id."""

from __future__ import annotations

import re
from datetime import datetime

from ..kernel import OrgError, stamp_of

BAD = "refused: since must be a date (2026-11-02), a datetime with offset or a message id: {since}. Nothing was read."
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_since(text: str) -> datetime:
    """``text`` as a time: a date ``YYYY-MM-DD`` is local midnight, an ISO datetime must carry its offset (``Z`` counts), a message id is its creation stamp. Anything else is an
    ``OrgError`` with the text of the design."""
    raw = text.strip()
    try:
        if _DATE.fullmatch(raw):
            return datetime.fromisoformat(raw).astimezone()
        if (stamp := stamp_of(raw)) is not None:
            return stamp
        found = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if found.tzinfo is not None:
            return found
    except ValueError:
        pass
    raise OrgError(BAD.format(since=raw))
