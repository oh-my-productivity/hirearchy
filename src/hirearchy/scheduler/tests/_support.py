"""Helpers of the tests of the run lifecycle."""

from __future__ import annotations

from pathlib import Path

from hirearchy.kernel import Message
from hirearchy.kernel.testing import FakeClock
from hirearchy.processes.testing import FakeProcessTable
from hirearchy.scheduler._run import PreparedRun, RunRecord
from hirearchy.scheduler.testing import NullSink

ROOT_DIR = Path("/memory/org")


def message(id: str = "20260101T000000000000-root-aaaa", sender: str = "root", trace: str | None = None, title: str = "t") -> Message:
    return Message(sender=sender, to="ceo", type="task", title=title, body="b", id=id, created="2026-01-01T00:00:00+00:00", trace=trace)


def prepared(addr: str = "ceo", batch: list[Message] | None = None, sink: NullSink | None = None, traces: tuple[str, ...] = (), budget: int | None = 3) -> PreparedRun:
    return PreparedRun(addr, batch if batch is not None else [message()], budget, ROOT_DIR / addr / "runs" / "20260101T000000000000.log", sink or NullSink(),
                       f"{addr}@20260101T000000000000", traces, "THE PROMPT")


def a_run(table: FakeProcessTable, clock: FakeClock, addr: str = "ceo", sink: NullSink | None = None, traces: tuple[str, ...] = ()) -> RunRecord:
    """A run in flight on a process of the table."""
    p = prepared(addr, sink=sink, traces=traces)
    handle = table.spawn(["kiro-cli"], cwd=ROOT_DIR, env={}, stdin=None, stdout=None)
    return RunRecord(addr, handle, p.log, p.sink, clock.time(), len(p.batch), None, p.run_id, traces, 3)
