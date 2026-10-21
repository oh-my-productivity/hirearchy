"""The messages of the history as the views see them: one record per id, with the boxes that hold a copy of it."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..kernel import JsonObject, parse_time, stamp_of
from ..mail import MessageFile

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


@dataclass
class Msg:
    id: str
    sender: str
    to: str
    type: str
    title: str
    status: str | None
    budget: int
    reply_to: str | None
    revises: str | None
    service: str | None
    feedback: str | None
    wake: bool
    trace: str | None  # as recorded in the frontmatter
    t: datetime
    boxes: list[tuple[str, str]] = field(default_factory=list)  # (owner, box) of every copy


def msg_time(mid: str, meta: JsonObject) -> datetime:
    """When a message was sent: the microsecond timestamp in its id, else its ``created`` second, else the epoch."""
    return stamp_of(mid) or parse_time(meta.get("created")) or _EPOCH


def _text(meta: JsonObject, key: str) -> str | None:
    return str(meta[key]) if meta.get(key) else None


def build_messages(files: Sequence[MessageFile]) -> dict[str, Msg]:
    out: dict[str, Msg] = {}
    for f in files:
        meta = f.meta
        if not meta or f.error:
            continue
        m = out.get(f.id)
        if m is None:
            try:
                budget = int(meta.get("budget") or 0)  # type: ignore[call-overload]
            except (TypeError, ValueError):
                budget = 0
            status = meta.get("status")
            m = out[f.id] = Msg(
                id=f.id, sender=str(meta["from"]), to=str(meta["to"]), type=str(meta["type"]),
                title=str(meta.get("title") or ""), status=status if status is None or isinstance(status, str) else str(status), budget=budget,
                reply_to=_text(meta, "reply_to"), revises=_text(meta, "revises"), service=_text(meta, "service"), feedback=_text(meta, "feedback"),
                wake=meta.get("wake", True) is not False,
                trace=_text(meta, "trace"),
                t=msg_time(f.id, meta),
            )
        elif not m.trace and meta.get("trace"):
            m.trace = str(meta["trace"])
        m.boxes.append((f.owner, f.box))
    return out
