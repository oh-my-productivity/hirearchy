"""Time vocabulary: aware datetimes, the timestamps in ids and file names, durations as text."""

from __future__ import annotations

from datetime import datetime
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
    raise NotImplementedError("red: K1")


def parse_time(value: object) -> datetime | None:
    """An aware datetime from the ISO strings (or YAML-parsed datetimes) in frontmatter; None when unreadable."""
    raise NotImplementedError("red: K1")


def stamp_of(name: str) -> datetime | None:
    """The time in the first 21 characters of an id or log file name; None when there is none."""
    raise NotImplementedError("red: K1")


def msg_time(m: Message) -> datetime | None:
    """When a message was sent: the microsecond timestamp in its id, else its ``created`` second."""
    raise NotImplementedError("red: K1")


def fmt_duration(seconds: float | None) -> str:
    """A coarse duration: ``45s``, ``7m``, ``3h``, ``2d``."""
    raise NotImplementedError("red: K1")


def fmt_dur(ms: float | None) -> str:
    """A duration given in milliseconds: ``850ms``, ``4.2s``, ``42s``, ``1m05s``, ``2h03m``."""
    raise NotImplementedError("red: K1")
