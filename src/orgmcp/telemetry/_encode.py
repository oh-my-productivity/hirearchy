"""One event as one JSON line of at most ``LINE_MAX`` bytes."""

from __future__ import annotations

import json

from ..eventlog import ENVELOPE, LINE_MAX
from ..kernel import JsonObject, clip

_SHRINKS = ((300, 25), (60, 5))  # (longest text, most items of a list or dict): tried in this order


def _default(value: object) -> str:
    return str(value)


def _dump(record: JsonObject) -> bytes:
    return json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=_default).encode("utf-8", "replace")


def encode_line(record: JsonObject) -> bytes:
    """The record as a UTF-8 line (with its newline). A line of ``LINE_MAX`` bytes or more is shrunk: fields clipped to 300 characters and
    25 items, else to 60 and 5 (``"truncated": true``), else the biggest fields are dropped one by one; as a last resort the line is cut.
    The envelope is never shrunk. Raises what ``str()`` or ``json`` raise for a value that cannot be written."""
    data = _dump(record)
    if len(data) < LINE_MAX:
        return data + b"\n"
    for text_limit, items in _SHRINKS:
        record = {k: (v if k in ENVELOPE else _shrink(v, text_limit, items)) for k, v in record.items()}
        record["truncated"] = True
        data = _dump(record)
        if len(data) < LINE_MAX:
            return data + b"\n"
    extra = sorted((k for k in record if k not in ENVELOPE and k != "truncated"), key=lambda k: -len(json.dumps(record[k], default=_default)))
    for k in extra:
        del record[k]
        data = _dump(record)
        if len(data) < LINE_MAX:
            break
    return data[: LINE_MAX - 1] + b"\n" if len(data) >= LINE_MAX else data + b"\n"


def _shrink(value: object, text_limit: int, items: int, depth: int = 0) -> object:
    if isinstance(value, str):
        return clip(value, text_limit)
    if depth > 4:
        return clip(value, text_limit)
    if isinstance(value, dict):
        return {str(k): _shrink(v, text_limit, items, depth + 1) for k, v in list(value.items())[:items]}
    if isinstance(value, (list, tuple, set)):
        return [_shrink(v, text_limit, items, depth + 1) for v in list(value)[:items]]
    return value
