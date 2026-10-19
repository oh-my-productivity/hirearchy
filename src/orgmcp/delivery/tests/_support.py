"""Helpers shared by the tests of ``delivery`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.delivery.testing import DeliveryHarness
from orgmcp.kernel import Message


def make(request: pytest.FixtureRequest, tmp_path: Path) -> DeliveryHarness:
    """The fixture body of the contract suite: the harness of one implementation, with the agents ``ceo`` and ``ceo/eng``."""
    h = cast(Callable[[Path], DeliveryHarness], request.param)(tmp_path)
    if h.mail is not None:
        for addr in ("ceo", "ceo/eng"):
            h.mail.agent(addr)
    return h


def task(sender: str = "root", to: str = "ceo", **kw: object) -> Message:
    """A message that still has to be completed: no id, no creation time, no trace."""
    msg = Message(sender=sender, to=to, type="task", body="the body", title="a title")
    for key, value in kw.items():
        setattr(msg, key, value)
    return msg
