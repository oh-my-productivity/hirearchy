"""The tools of the human's seat: observe, create_org, start and stop, progress."""

from __future__ import annotations

import asyncio
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from orgmcp.attention import Waiting
from orgmcp.attention.testing import FixedOpenWork, FixedWaiting
from orgmcp.daemon import SchedulerState
from orgmcp.daemon.testing import FakeSchedulerControl, FakeSchedulerStatus
from orgmcp.kernel import ROOT, OrgError, OrgPaths
from orgmcp.mcp_server._instructions import InstructionText
from orgmcp.mcp_server._tools_observe import ObservabilityTools
from orgmcp.mcp_server._tools_progress import ProgressTools
from orgmcp.mcp_server._tools_scheduler import SchedulerTools
from orgmcp.mcp_server._tools_setup import RootSetupTools
from orgmcp.mcp_server.testing import MemoryBinding
from orgmcp.observability.testing import FixedObservabilityText
from orgmcp.progress import WAIT_MAX
from orgmcp.progress.testing import FixedProgressReporter

from ._support import call, fails, serve

HERE = Path("/memory/org")


# ------------------------------------------------------------------------------------------------------------- observe


def test_observe_asks_for_the_view_with_the_arguments_as_given_and_their_defaults() -> None:
    text = FixedObservabilityText("THE VIEW")
    server = serve(ObservabilityTools(lambda: text), ROOT)
    assert call(server, "observe") == "THE VIEW"
    assert call(server, "observe", view="trace", target="t1", since="7d", by="tool", errors_only=True, limit=5) == "THE VIEW"
    first, second = text.asked
    assert (first["view"], first["target"], first["since"], first["by"], first["errors_only"], first["limit"]) == ("now", None, "24h", None, False, 50)
    assert (second["view"], second["target"], second["since"], second["by"], second["errors_only"], second["limit"]) == ("trace", "t1", "7d", "tool", True, 5)


def test_a_refused_view_is_the_refusal_of_the_tool() -> None:
    server = serve(ObservabilityTools(lambda: FixedObservabilityText(fails=OrgError("unknown view"))), ROOT)
    assert "unknown view" in fails(server, "observe", view="nope")


# ------------------------------------------------------------------------------------------------------------- create_org


def test_create_org_creates_it_and_says_what_comes_next() -> None:
    binding = MemoryBinding(HERE)
    out = call(serve(RootSetupTools(binding), ROOT), "create_org", mission="A mission", default_model="m", path=None)
    assert out == ("created the organization at /memory/org. Next: hire a team (hire), give it work (delegate), then "
                   "start() the scheduler. Use only this organization.")
    assert binding.created == [("A mission", "m", None)]


def test_create_org_refusals_are_the_bindings() -> None:
    assert "mission is required" in fails(serve(RootSetupTools(MemoryBinding(HERE)), ROOT), "create_org", mission="")
    assert "already exists" in fails(serve(RootSetupTools(MemoryBinding(HERE, exists=True)), ROOT), "create_org", mission="m")


# ------------------------------------------------------------------------------------------------------------- start / stop


def scheduler(status: FakeSchedulerStatus | None = None, idle: bool = False, waiting: Waiting | None = None) -> tuple[SchedulerTools, FakeSchedulerControl, FixedOpenWork, FixedWaiting]:
    status = status or FakeSchedulerStatus()
    control, work, wait = FakeSchedulerControl(status), FixedOpenWork(idle), FixedWaiting(waiting)
    return SchedulerTools(lambda: control, lambda: status, lambda: wait, lambda: work, lambda: OrgPaths(HERE)), control, work, wait


def test_start_starts_the_scheduler_and_says_where_its_log_is() -> None:
    group, control, _, _ = scheduler()
    out = call(serve(group, ROOT), "start", max_runs=2)
    assert out == "scheduler started (pid 4242, at most 2 run(s); it exits by itself when the work is done); log: /memory/org/.runtime/scheduler.log"
    assert control.starts == [(2, True)]


def test_start_without_until_done_says_it_runs_until_stopped() -> None:
    group, control, _, _ = scheduler()
    assert call(serve(group, ROOT), "start", until_done=False) == "scheduler started (pid 4242; it runs until stop()); log: /memory/org/.runtime/scheduler.log"
    assert control.starts == [(None, False)]


def test_start_has_nothing_to_start_when_there_is_nothing_to_do() -> None:
    group, control, _, _ = scheduler(idle=True)
    assert call(serve(group, ROOT), "start").startswith("not started: there is nothing to run (you have no open task and no agent has work).")
    assert control.starts == []
    assert call(serve(group, ROOT), "start", until_done=False).startswith("scheduler started")  # an idle scheduler may be kept running


def test_start_refuses_when_nothing_can_progress_without_the_user() -> None:
    waiting = Waiting("waiting on you: ceo needs budget (ceo out of runs)", "Your options: send(to=\"ceo\", body=\"<why>\", budget=N)")
    group, control, _, _ = scheduler(waiting=waiting)
    for until_done in (True, False):
        out = call(serve(group, ROOT), "start", until_done=until_done)
        assert out == ("not started: nothing can progress without you, so a scheduler would only sit idle. waiting on you: ceo needs budget (ceo out of runs). "
                       "Your options: send(to=\"ceo\", body=\"<why>\", budget=N)")
    assert control.starts == []


def test_start_does_not_ask_why_when_a_scheduler_runs_and_the_control_refuses() -> None:
    status = FakeSchedulerStatus(SchedulerState("running", 9, "then"))
    group, _, work, wait = scheduler(status, idle=True, waiting=Waiting("waiting on you: x", "o"))
    assert "already running" in fails(serve(group, ROOT), "start")
    assert work.asked == [] and wait.asked == []  # the questions are asked only of a stopped scheduler


def test_stop_stops_it_or_says_there_is_none() -> None:
    status = FakeSchedulerStatus(SchedulerState("running", 9, "then"))
    group, control, _, _ = scheduler(status)
    assert call(serve(group, ROOT), "stop") == "scheduler stopped (pid 9)"
    assert call(serve(group, ROOT), "stop") == "no scheduler is running for this org"
    assert control.stops == [15.0, 15.0]


# ------------------------------------------------------------------------------------------------------------- progress


def test_progress_describes_it_in_a_worker_thread_and_clamps_the_wait() -> None:
    reporter = FixedProgressReporter(described="THE STATUS")
    group = ProgressTools(InstructionText(MemoryBinding(HERE, exists=True)), lambda: reporter)
    server = serve(group, ROOT)
    assert call(server, "progress") == "THE STATUS"
    call(server, "progress", task_id="t1", wait_seconds=30)
    call(server, "progress", wait_seconds=-5)
    call(server, "progress", wait_seconds=10_000)
    assert [(c[1], c[3]) for c in reporter.calls] == [(None, 0), ("t1", 30), (None, 0), (None, WAIT_MAX)]


def test_progress_is_async_and_before_the_organization_exists_it_is_the_setup_state() -> None:
    group = ProgressTools(InstructionText(MemoryBinding(HERE)), lambda: FixedProgressReporter())
    server = serve(group, ROOT)
    tool = server._tool_manager.list_tools()[0]
    assert asyncio.iscoroutinefunction(tool.fn)
    assert call(server, "progress", wait_seconds=60).startswith("Setup: no organization exists at /memory/org yet.")
