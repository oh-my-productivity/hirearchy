"""Helpers shared by the tests of ``attention`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.attention.testing import AttentionWorld
from orgmcp.kernel import ROOT, Message


RED = pytest.mark.xfail(strict=True, reason="red: C-attention")


def make_world(request: pytest.FixtureRequest, tmp_path: Path) -> AttentionWorld:
    """The fixture body of a contract suite: the world of one implementation."""
    return cast(Callable[[Path], AttentionWorld], request.param)(tmp_path)


def give(w: AttentionWorld, to: str = "ceo", title: str = "Ship it", runs: int = 5) -> Message:
    """Root gives a task to ``to`` (hired if it is not yet; ``ceo/eng`` needs ``ceo`` first)."""
    w.hire(to)
    return w.delegate(ROOT, to, title, runs)


def stalled_on_budget(w: AttentionWorld) -> Message:
    """Root's only task sits with ``ceo``, which has used its single run: the task is unread and cannot be served."""
    task = give(w, "ceo", "Rework the report", 1)
    w.use_run("ceo")
    assert w.budget("ceo") == 0
    return task


def read_it(w: AttentionWorld, addr: str) -> None:
    """``addr`` read what it had in its inbox, in a run that ended well: it holds the task and nothing runs."""
    w.begin_run(addr)
    w.end_run(addr)
