"""``status health progress dash`` over fakes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hirearchy.cli._commands_views import DashCommand, HealthCommand, ProgressCommand, StatusCommand
from hirearchy.cli.testing import RecordingDashboardRunner, ScriptedTerminal
from hirearchy.kernel import Message

from ._fakes import FakeReadings, agent_health, new_readings
from ._support import Fixture, go



def test_status_shows_the_tree_then_the_tasks_root_gave_then_the_scheduler(tmp_path: Path) -> None:
    f, readings = Fixture(tmp_path), new_readings()
    readings.outstanding_tasks = [Message("root", "ceo", "task", "g", title="Ship it", id="t-1"), Message("root", "ceo/eng", "task", "g", title="Fix", id="t-2")]
    go(StatusCommand(f.session, lambda: readings, lambda: readings, lambda: readings, f.out), "status")
    assert f.session.calls == [("open", False)]
    assert f.out.stdout == (
        "root (human): unread 0, delegated 0\n\nyour outstanding tasks:\n  t-1 \"Ship it\" -> ceo\n  t-2 \"Fix\" -> ceo/eng\n\nscheduler: stopped\n"
    )
    assert readings.last("outstanding") == (("root",), {})


def test_status_without_tasks_leaves_out_their_heading(tmp_path: Path) -> None:
    f, readings = Fixture(tmp_path), new_readings()
    go(StatusCommand(f.session, lambda: readings, lambda: readings, lambda: readings, f.out), "status")
    assert f.out.stdout == "root (human): unread 0, delegated 0\n\nscheduler: stopped\n"


def test_cli_status_does_not_show_it(tmp_path: Path) -> None:
    """The terminal is the user's own seat: `status` never asks the progress text (where the deliverable note lives)."""
    f, readings = Fixture(tmp_path), new_readings()
    go(StatusCommand(f.session, lambda: readings, lambda: readings, lambda: readings, f.out), "status")
    assert "describe_progress" not in readings.names() and "Deliverable" not in f.out.stdout


def test_health_renders_the_report_of_the_whole_organization(tmp_path: Path) -> None:
    f, readings = Fixture(tmp_path), new_readings()
    go(HealthCommand(f.session, lambda: readings, lambda: readings, f.out), "health")
    assert readings.last("org_health") == (("root",), {})
    assert f.out.stdout == "0 agents, 0 flagged\n"


def test_health_of_one_agent_as_structured_data(tmp_path: Path) -> None:
    f, readings = Fixture(tmp_path), new_readings()
    go(HealthCommand(f.session, lambda: readings, lambda: readings, f.out), "health", "--agent", "ceo", "--json")
    assert readings.last("org_health") == (("ceo",), {}) and "render_text" not in readings.names()
    data = json.loads(f.out.stdout)
    assert data["root"] == "ceo" and data["flagged"] == []


def test_progress_asks_for_one_task_and_how_long_to_wait(tmp_path: Path) -> None:
    f, readings = Fixture(tmp_path), new_readings()
    go(ProgressCommand(f.session, lambda: readings, f.out), "progress", "t-1", "--wait", "30")
    assert f.session.calls == [("open", False)]
    assert readings.last("describe_progress") == (("t-1", 30), {}) and f.out.stdout == "progress text\n"
    go(ProgressCommand(f.session, lambda: readings, f.out), "progress")
    assert readings.last("describe_progress") == ((None, 0), {})


def dash_world(tmp_path: Path, interactive: bool) -> tuple[Fixture, FakeReadings, RecordingDashboardRunner, DashCommand]:
    f, readings, runner = Fixture(tmp_path), new_readings(), RecordingDashboardRunner()
    return f, readings, runner, DashCommand(f.session, lambda: readings, runner, ScriptedTerminal(interactive), f.out)


def test_dash_once_prints_the_snapshot_even_on_a_terminal(tmp_path: Path) -> None:
    f, readings, runner, command = dash_world(tmp_path, True)
    go(command, "dash", "--once")
    assert f.out.stdout == "once text\n" and runner.runs == []
    assert f.session.calls == [("open", False)]  # read-only: nothing is announced and nothing is recorded


def test_dash_without_a_terminal_prints_the_snapshot(tmp_path: Path) -> None:
    f, readings, runner, command = dash_world(tmp_path, False)
    go(command, "dash")
    assert f.out.stdout == "once text\n" and runner.runs == []


def test_dash_on_a_terminal_runs_the_full_screen_dashboard_of_the_opened_organization(tmp_path: Path) -> None:
    f, readings, runner, command = dash_world(tmp_path, True)
    go(command, "dash", "--interval", "5")
    assert runner.runs == [(tmp_path / "org", 5.0)] and f.out.stdout == "" and readings.calls == []


def test_dash_takes_its_root_after_the_command_too(tmp_path: Path) -> None:
    from ._support import parse

    f, readings, runner, command = dash_world(tmp_path, False)
    assert parse(command, "dash", "--root", "/x/org", "--once").root == "/x/org"
    assert parse(command, "dash", "--once", root="/y/org").root == "/y/org"  # the global one
    assert parse(command, "dash", "--root", "/x/org", "--once", root="/y/org").root == "/x/org"  # the one given last, to the command, wins
    assert not hasattr(parse(command, "dash"), "root") or parse(command, "dash").root is None
