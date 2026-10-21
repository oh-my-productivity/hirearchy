"""Helpers shared by the tests of ``dashdata`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.dashdata.testing import DashWorld, FeedWorld, StateWorld
from hirearchy.daemon import SchedulerState
from hirearchy.kernel import Message
from hirearchy.observability.testing import stamp

__all__ = ["bad_message", "make_feed", "make_state", "make_world", "running_scheduler", "stamp", "team"]

UP = SchedulerState("running", 7000, "2026-10-18 10:00:00Z")


def make_world(request: pytest.FixtureRequest, tmp_path: Path) -> DashWorld:
    """The fixture body of a contract suite: the world of one implementation."""
    return cast(Callable[[Path], DashWorld], request.param)(tmp_path)


def make_feed(request: pytest.FixtureRequest, tmp_path: Path) -> FeedWorld:
    return cast(Callable[[Path], FeedWorld], request.param)(tmp_path)


def make_state(request: pytest.FixtureRequest, tmp_path: Path) -> StateWorld:
    return cast(Callable[[Path], StateWorld], request.param)(tmp_path)


def team(w: DashWorld) -> None:
    """``ceo`` with ``ceo/analyst`` and ``ceo/writer`` below it, and ``ops``; each holds some runs."""
    for addr in ("ceo", "ceo/analyst", "ceo/writer", "ops"):
        w.obs.agent(addr)
    w.obs.budgets.held.update({"ceo": 3, "ceo/analyst": 4, "ceo/writer": 2, "ops": 2})


def running_scheduler(w: DashWorld, max_parallel: int = 2) -> None:
    """A scheduler is running (pid 7000, started at t=0, beating at t=197) and the organization allows ``max_parallel`` runs at once."""
    w.obs.scheduler.current = UP
    w.obs.configure(f"---\nmission: test\nmax_parallel: {max_parallel}\n---\nrules\n")
    w.obs.emit(0, "scheduler.start", proc="scheduler", pid=7000, mode="until_done", max_runs=None, max_parallel=max_parallel, version="x")
    w.obs.emit(197, "scheduler.heartbeat", proc="scheduler", pid=7000, running=[], runnable=0, waiting_on_you=0)


def bad_message(w: DashWorld, addr: str, box: str = "inbox") -> Message:
    """A file in the box that is not a message (the front matter does not parse), written behind everyone's back."""
    name = f"{stamp(1):%Y%m%dT%H%M%S%f}-root-bad0.md"
    directory = w.root / ("" if addr == "root" else addr) / box
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text("---\nfrom: [oops\n---\nx\n", encoding="utf-8")
    return Message(sender="root", to=addr, type="note", title="bad", body="x", id=name[:-3])
