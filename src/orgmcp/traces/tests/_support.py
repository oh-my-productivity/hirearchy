"""Helpers shared by the tests of ``traces`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import ROOT, Message, join_frontmatter
from orgmcp.traces.testing import TraceHarness


def make(request: pytest.FixtureRequest, tmp_path: Path) -> TraceHarness:
    """The fixture body of every contract suite: the harness of one implementation, with the agents ``ceo`` and ``ceo/eng``."""
    h = cast(Callable[[Path], TraceHarness], request.param)(tmp_path)
    agents(h, "ceo", "ceo/eng")
    return h


def agents(h: TraceHarness, *addrs: str) -> None:
    """Make every address an agent."""
    for addr in addrs:
        h.mail.agent(addr)


def mid(n: int, sender: str = "root") -> str:
    """A message id that sorts by ``n``: ``<UTC stamp>-<sender>-<4 hex>``."""
    return f"20260101T000000{n:06d}-{sender.replace('/', '.')}-aaaa"


def where(addr: str, box: str, msg_id: str) -> str:
    """The path of a message file, relative to the organization (the boxes of root are in the organization itself)."""
    return f"{box}/{msg_id}.md" if addr == ROOT else f"{addr}/{box}/{msg_id}.md"


def put(h: TraceHarness, addr: str, box: str, n: int, **kw: object) -> str:
    """Message file number ``n`` in a box of ``addr``; returns its id. ``sender`` defaults to root, ``to`` to ``addr``, ``kind`` to a task."""
    sender = str(kw.pop("sender", "root"))
    msg_id = mid(n, sender)
    meta: dict[str, object] = {
        "id": msg_id, "from": sender, "to": kw.pop("to", addr), "type": kw.pop("kind", "task"), "title": "t",
        "created": "2026-01-01T00:00:00+00:00", "hops": 0,
    }
    meta.update(kw)
    h.mail.put(where(addr, box, msg_id), join_frontmatter(meta, "body"))
    return msg_id


def result(h: TraceHarness, addr: str, n: int, task_id: str, status: str = "done") -> str:
    """A result ``addr`` sent for ``task_id`` (in its ``sent`` box)."""
    return put(h, addr, "sent", n, sender=addr, to="root", kind="result", reply_to=task_id, status=status)


def message(sender: str, to: str, kind: str = "task", n: int = 90, **kw: object) -> Message:
    """A message that is about to be delivered: id and creation time complete, no trace yet."""
    msg = Message(sender=sender, to=to, type=kind, body="b", title="t", id=mid(n, sender), created="2026-01-01T00:00:00+00:00")
    for key, value in kw.items():
        setattr(msg, key, value)
    return msg
