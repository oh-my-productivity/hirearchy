"""The event encoder and argument summary of the first version, frozen verbatim from commit ``8323897`` (``r1-integration``, ``hirearchy/telemetry.py``).

``_encode``, ``_shrink`` and ``summarize_args`` move into the package in step A-telemetry, so the live code cannot serve as its own
oracle; these copies do (only the module constants come from ``hirearchy.eventlog`` and ``clip`` from the kernel, where the former module got
them). They are the reference of the byte-compatibility tests and stay as long as those tests do.
"""

from __future__ import annotations

import json
from typing import Any

from hirearchy.eventlog import ENVELOPE, LINE_MAX
from hirearchy.kernel import TITLE_MAX, clip


def _default(value: object) -> str:
    return str(value)


def encode(record: dict[str, Any]) -> bytes:
    """One JSON line; shrunk to ``LINE_MAX`` bytes when it is longer (fields clipped, then dropped, ``truncated``)."""
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=_default)
    data = line.encode("utf-8", "replace")
    if len(data) < LINE_MAX:
        return data + b"\n"
    for text_limit, items in ((300, 25), (60, 5)):
        record = {k: (v if k in ENVELOPE else _shrink(v, text_limit, items)) for k, v in record.items()}
        record["truncated"] = True
        data = json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=_default).encode("utf-8", "replace")
        if len(data) < LINE_MAX:
            return data + b"\n"
    extra = sorted((k for k in record if k not in ENVELOPE and k != "truncated"),
                   key=lambda k: -len(json.dumps(record[k], default=_default)))
    for k in extra:
        del record[k]
        data = json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=_default).encode("utf-8", "replace")
        if len(data) < LINE_MAX:
            break
    return data[: LINE_MAX - 1] + b"\n" if len(data) >= LINE_MAX else data + b"\n"


def _shrink(value: Any, text_limit: int, items: int, depth: int = 0) -> Any:
    if isinstance(value, str):
        return clip(value, text_limit)
    if depth > 4:
        return clip(value, text_limit)
    if isinstance(value, dict):
        return {str(k): _shrink(v, text_limit, items, depth + 1) for k, v in list(value.items())[:items]}
    if isinstance(value, (list, tuple, set)):
        return [_shrink(v, text_limit, items, depth + 1) for v in list(value)[:items]]
    return value


_KEEP_STR = {
    "to": 200, "task_id": 200, "status": 40, "name": 80, "owner": 200, "service": 80, "verdict": 20, "report": 200,
    "agent": 200, "path": 300, "reply_to": 200, "revises": 200, "view": 40, "target": 200, "since": 80, "until": 80,
    "by": 40, "model": 80, "workspace": 300, "kind": 40, "plan_id": 80, "role": 80, "title": TITLE_MAX,
}
_KEEP_LIST = {"inputs", "artifacts", "tools"}


def summarize_args(arguments: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, value in arguments.items():
        if value is None:
            continue  # an argument left at its default says nothing
        if isinstance(value, (bool, int, float)):
            out[name] = value
        elif isinstance(value, str):
            if name in _KEEP_STR:
                out[name] = clip(value, _KEEP_STR[name])
            else:
                out[f"{name}_chars"] = len(value)
        elif isinstance(value, dict):
            out[f"{name}_keys"] = [clip(k, 60) for k in list(value)[:20]]
        elif isinstance(value, (list, tuple)):
            if name in _KEEP_LIST and all(isinstance(v, str) for v in value):
                out[name] = [clip(v, 200) for v in value[:20]] + (["…"] if len(value) > 20 else [])
            else:
                out[f"{name}_n"] = len(value)
                chars = sum(len(v) for v in value if isinstance(v, str))
                if chars:
                    out[f"{name}_chars"] = chars
        else:
            out[f"{name}_type"] = type(value).__name__
    return out
