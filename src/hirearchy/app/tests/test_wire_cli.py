"""``wire_cli``: the command line over a real organization - the 25 commands in the order of the parser, the session that opens the runtime, the process's own
output and terminal, the tail of the event files, the scheduler's loop and the other entry points behind their ports, the plan before there is an organization."""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy.app import Org, fields_cli, wire_cli, wire_dashboard, wiring
from hirearchy.app.wire_locator import os_locator
from hirearchy.cli import CliApp
from hirearchy.cli._session import AnnouncingOrgSession
from hirearchy.cli.testing import MemoryOutput
from hirearchy.dashboard.testing import FakeDashboardLauncher
from hirearchy.hierarchy import Hiring
from hirearchy.kernel import ROOT, OrgError
from hirearchy.kernel.testing import FakeClock


COMMANDS = [
    "init", "hire", "task", "services", "define-service", "request", "feedback", "retire-service", "plan", "apply", "send", "status", "health", "progress",
    "upgrade-rules", "install-skill", "review", "inbox", "resume", "run", "mcp", "dash", "obs", "check", "kiro-profile",
]


@pytest.fixture
def team(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire(ROOT, "ceo", "Chief", "Lead.", can_hire=True)
    return made


def test_the_program_is_the_command_line_with_the_25_commands_in_order() -> None:
    assert isinstance(wire_cli.cli_app(), CliApp)
    session = AnnouncingOrgSession(os_locator(), wire_cli.RuntimeOrgOpener(), wire_cli.StandardOutput())
    commands = wire_cli.commands_over(session, wire_cli.StandardOutput(), wire_cli.StandardTerminal(), FakeClock())
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    for command in commands:
        command.add_arguments(sub)
    assert list(sub.choices) == COMMANDS and all(callable(c.run) for c in commands)


def test_the_wiring_has_no_port_of_its_own() -> None:
    assert fields_cli.STEP == "D-cli" and "CliApp" in fields_cli.NOT_A_FIELD
    assert wire_cli.register in wiring.registrars()


def test_the_output_and_the_terminal_are_the_standard_ones_looked_up_at_each_call(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    out = wire_cli.StandardOutput()
    out.say("one")
    out.say()
    out.write("two")
    out.warn("three")
    captured = capsys.readouterr()
    assert captured.out == "one\n\ntwo" and captured.err == "three\n"
    terminal = wire_cli.StandardTerminal()

    class Tty(io.StringIO):
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr("sys.stdin", Tty())
    monkeypatch.setattr("sys.stdout", io.StringIO())
    assert terminal.stdout_is_tty() is False and terminal.is_interactive() is False
    monkeypatch.setattr("sys.stdout", Tty())
    assert terminal.stdout_is_tty() is True and terminal.is_interactive() is True


def test_json_is_indented_and_made_of_text(tmp_path: Path) -> None:
    dump = wire_cli.PlainJson().dump({"at": datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc), "path": tmp_path, "tags": ("a", "b"), "set": {1}})
    assert dump == json.dumps({"at": "2026-01-15T09:00:00+00:00", "path": str(tmp_path), "tags": ["a", "b"], "set": [1]}, indent=2)


def test_the_opener_opens_an_organization_and_refuses_a_directory_that_is_none(team: Org, tmp_path: Path) -> None:
    opener = wire_cli.RuntimeOrgOpener()
    ports = opener.open(team.root)
    assert ports.root == team.root and isinstance(ports.get(Hiring), Hiring)
    with pytest.raises(OrgError, match="not an organization"):
        opener.open(tmp_path / "nowhere")
    assert opener.prepare(tmp_path / "nowhere").root == tmp_path / "nowhere"


def test_a_provider_asks_the_organization_the_session_opened_last(team: Org) -> None:
    session = AnnouncingOrgSession(os_locator(), wire_cli.RuntimeOrgOpener(), MemoryOutput())
    hiring = wire_cli.of(session, Hiring)
    with pytest.raises(OrgError, match="no organization is open"):
        hiring()
    session.open(argparse.Namespace(root=str(team.root)))
    assert isinstance(hiring(), Hiring)


def test_the_tail_sees_the_events_written_after_it_started(team: Org) -> None:
    ports = wire_cli.RuntimeOrgOpener().open(team.root)
    tails = wire_cli.RuntimeEventTails(ports)
    assert tails.any() is True  # (the hire above is an event)
    tail = tails.follow(None, "custom.kind", None, False)
    assert tail.poll() == []
    team.emit("custom.kind", n=1)
    team.emit("other.kind", n=2)
    assert [e["n"] for e in tail.poll()] == [1] and tail.poll() == []


def test_a_new_organization_has_no_event_files(tmp_path: Path) -> None:
    root = tmp_path / "bare"
    (root).mkdir()
    (root / "ORG.md").write_text("---\nmission: m\n---\n", encoding="utf-8")
    assert wire_cli.RuntimeEventTails(wire_cli.RuntimeOrgOpener().open(root)).any() is False


def test_the_scheduler_runner_runs_the_loop_until_there_is_nothing_to_do(team: Org) -> None:
    out = MemoryOutput()
    runner = wire_cli.LoopSchedulerRunner(out, FakeClock())
    runner.run(team.root, "kiro-cli", once=False, until_idle=False, until_done=True, max_runs=None)
    assert out.stdout == "scheduler exiting: finished: no open tasks\n"
    out.events.clear()
    runner.run(team.root, "kiro-cli", once=True, until_idle=False, until_done=False, max_runs=None)
    assert out.stdout == ""  # (one pass, nothing to run)


def test_the_launchers_of_the_other_entry_points_import_them_only_when_they_run(team: Org, monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[object] = []
    fake = FakeDashboardLauncher({team.root})
    monkeypatch.setattr(wire_dashboard, "dashboard_launcher", lambda screens=None: fake)
    wire_cli.LazyDashboardRunner().run(team.root, 3.0)
    assert fake.launched == [(team.root, 3.0)]

    class Server:
        def run(self) -> None:
            started.append("served")

    monkeypatch.setattr(wire_cli, "mcp_server_runner", lambda: Server())
    wire_cli.LazyMcpRunner().run()
    assert started[-1] == "served"


def test_the_plan_of_a_blueprint_is_checked_without_an_organization_against_the_defaults() -> None:
    validator, renderer = wire_cli.PlanTime().get()
    bp = {"mission": "m", "agents": [{"name": "lead", "template": "manager"}]}
    issues = validator.validate(bp, org_exists=False)
    assert [i.path for i in issues if i.level == "error"] and "Plan for approval" in renderer.render_plan(bp, issues)
    assert wire_cli.PlanTime().get() is not None


def test_the_snapshot_of_dash_once_comes_from_the_runtime_of_the_dashboard(team: Org) -> None:
    session = AnnouncingOrgSession(os_locator(), wire_cli.RuntimeOrgOpener(), MemoryOutput())
    session.open(argparse.Namespace(root=str(team.root)))
    assert "hirearchy dash" in wire_cli.snapshot_renderer_of(session)().render_once()


def test_nothing_but_the_run_of_a_command_imports_the_framework_of_the_server_or_of_the_screen() -> None:
    code = textwrap.dedent("""
        import sys
        from hirearchy.app import wire_cli
        wire_cli.cli_app()
        print([m for m in ("textual", "mcp.server.fastmcp", "hirearchy.dashboard") if m in sys.modules])
    """)
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "[]"
