"""Helpers shared by the tests of ``stalls`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import Message
from hirearchy.stalls.testing import STALL_AFTER, NudgesHarness, StallsWorld


def make_world(request: pytest.FixtureRequest, tmp_path: Path) -> StallsWorld:
    """The fixture body of the ladder's contract suite: the world of one implementation."""
    return cast(Callable[[Path], StallsWorld], request.param)(tmp_path)


def make_nudges(request: pytest.FixtureRequest, tmp_path: Path) -> NudgesHarness:
    """The fixture body of the ledger's contract suite: the harness of one implementation."""
    return cast(Callable[[Path], NudgesHarness], request.param)(tmp_path)


def titles(w: StallsWorld, addr: str) -> list[str]:
    """The titles of the notes of the runtime ``addr`` has received."""
    return [m.title for m in w.notes(addr)]


def quiet_task(w: StallsWorld, to: str = "ceo", sender: str = "root", title: str = "T") -> Message:
    """``to`` (hired, with ``sender`` if need be) has been given a task and has read it, and then nothing happened: a task that will stall."""
    for addr in {sender, to}:
        if addr != "root":
            w.hire(addr)
    task = w.delegate(sender, to, title)
    w.read(to)
    return task


def stall(w: StallsWorld) -> list[str]:
    """Let ``stall_after`` pass and run one pass of the ladder."""
    w.clock.advance(STALL_AFTER)
    return w.ladder.check()


def stall_at(w: StallsWorld) -> tuple[list[str], float]:
    """Like ``stall``, and the time the pass read from the clock (delivering a note moves the fake clock on by a microsecond)."""
    w.clock.advance(STALL_AFTER)
    at = w.clock.time()
    return w.ladder.check(), at
