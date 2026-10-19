"""Org files that a built-in ``write`` left in the workspace are warned about, in the log and the output, and remembered once."""

from __future__ import annotations

from pathlib import Path

from orgmcp.processes.testing import FakeProcessTable
from orgmcp.kernel.testing import FakeClock
from orgmcp.scheduler._strays import StrayCheck
from orgmcp.scheduler.testing import NullSink, RecordingConsole
from orgmcp.strays.testing import MemoryStrays

from ._support import a_run

WORKSPACE = Path("/ws")


def writer() -> MemoryStrays:
    strays = MemoryStrays()
    strays.put_agent("dev", {"tools": ["write"], "workspace": str(WORKSPACE)})
    return strays


def test_what_appeared_during_the_run_is_warned_about_and_recorded() -> None:
    strays, console, sink = writer(), RecordingConsole(), NullSink()
    check = StrayCheck(strays, strays, console)
    run = a_run(FakeProcessTable(), FakeClock(), "dev", sink)
    run.strays = check.before("dev")
    strays.touch(WORKSPACE / "dev", 5.0)
    strays.touch(WORKSPACE / "dev" / "MEMORY.md", 5.0)
    check.after(run)
    shown = str(WORKSPACE / "dev")
    assert sink.text == f"\n# warning: dev created org files in its workspace with the built-in `write` (not in the org, so they are not its memory): {shown}\n"
    assert console.lines == [f"dev: warning: org files in its workspace (built-in write shadows orgmcp write?): {shown}"]
    assert "write" in strays.take_notice("dev")  # told once: the next prompt carries it


def test_nothing_new_nothing_said() -> None:
    strays, console, sink = writer(), RecordingConsole(), NullSink()
    strays.touch(WORKSPACE / "dev", 1.0)
    check = StrayCheck(strays, strays, console)
    run = a_run(FakeProcessTable(), FakeClock(), "dev", sink)
    run.strays = check.before("dev")
    check.after(run)
    assert (sink.text, console.lines, strays.take_notice("dev")) == ("", [], "")


def test_a_run_without_a_probe_before_it_is_not_checked_after() -> None:
    strays, console, sink = writer(), RecordingConsole(), NullSink()
    run = a_run(FakeProcessTable(), FakeClock(), "dev", sink)
    strays.touch(WORKSPACE / "dev", 5.0)
    StrayCheck(strays, strays, console).after(run)
    assert (sink.text, console.lines) == ("", [])
