"""One event as one JSON line of at most ``LINE_MAX`` bytes."""

from __future__ import annotations

from ..kernel import JsonObject


def encode_line(record: JsonObject) -> bytes:
    """The record as a UTF-8 line (with its newline); shrunk when it does not fit (fields clipped, then dropped, ``truncated``)."""
    raise NotImplementedError("red: A-telemetry")
