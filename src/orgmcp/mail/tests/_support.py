"""Helpers shared by the tests of ``mail`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import ROOT, Message, join_frontmatter
from orgmcp.mail.testing import MailHarness, ParserHarness

BAD_YAML = "---\nfrom: [unclosed\nto: ceo\n---\nbody\n"  # the front matter does not parse
BAD_BUDGET = "---\nfrom: root\nto: ceo\ntype: task\nbudget: lots\n---\nbody\n"  # parses, but the message does not build


def make(request: pytest.FixtureRequest, tmp_path: Path) -> MailHarness:
    """The fixture body of every contract suite: the harness of one implementation."""
    return cast(Callable[[Path], MailHarness], request.param)(tmp_path)


def make_parser(request: pytest.FixtureRequest, tmp_path: Path) -> ParserHarness:
    return cast(Callable[[Path], ParserHarness], request.param)(tmp_path)


def mid(n: int, sender: str = "root") -> str:
    """A message id that sorts by ``n``: ``<UTC stamp>-<sender>-<4 hex>``."""
    return f"20260101T000000{n:06d}-{sender.replace('/', '.')}-aaaa"


def where(addr: str, box: str, msg_id: str) -> str:
    """The path of a message file, relative to the organization (the boxes of root are in the organization itself)."""
    return f"{box}/{msg_id}.md" if addr == ROOT else f"{addr}/{box}/{msg_id}.md"


def message_text(msg_id: str, *, sender: str = "root", to: str = "ceo", kind: str = "task", body: str = "body", **extra: object) -> str:
    """The text of a message file."""
    meta: dict[str, object] = {"id": msg_id, "from": sender, "to": to, "type": kind, "title": "t", "created": "2026-01-01T00:00:00+00:00", "hops": 0}
    meta.update(extra)
    return join_frontmatter(meta, body)


def put(h: MailHarness, addr: str, box: str, n: int, **kw: object) -> str:
    """A message file number ``n`` in a box of ``addr``; returns its id. ``sender`` defaults to root, ``to`` to ``addr``."""
    msg_id = mid(n, str(kw.get("sender", "root")))
    kw.setdefault("to", addr)
    h.put(where(addr, box, msg_id), message_text(msg_id, **kw))  # type: ignore[arg-type]
    return msg_id


def agents(h: MailHarness, *addrs: str) -> None:
    """Make every address an agent."""
    for addr in addrs:
        h.agent(addr)


def note(n: int, *, sender: str = "ceo", to: str = "ceo/eng", kind: str = "task", body: str = "do it", **kw: object) -> Message:
    """A message to store, with its id and creation time complete (as ``deliver`` leaves it)."""
    msg = Message(sender=sender, to=to, type=kind, body=body, title="t", id=mid(n, sender), created="2026-01-01T00:00:00+00:00")
    for key, value in kw.items():
        setattr(msg, key, value)
    return msg


def raises_a_parse_error(call: Callable[[], object]) -> None:
    """``call`` fails because a file does not parse (the yaml error, or the bad number), not because the code is not there yet."""
    with pytest.raises(Exception) as caught:
        call()
    assert type(caught.value).__name__ in {"ParserError", "ScannerError", "ConstructorError", "ValueError"}, repr(caught.value)
