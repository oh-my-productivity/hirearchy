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

from orgmcp.app import Org
from orgmcp.cli import CliApp
from orgmcp.cli.testing import MemoryOutput
from orgmcp.hierarchy import Hiring
from orgmcp.kernel import ROOT, OrgError
from orgmcp.kernel.testing import FakeClock

pytestmark = pytest.mark.xfail(strict=True, reason="red: D-cli")

COMMANDS = [
    "init", "hire", "task", "services", "define-service", "request", "feedback", "retire-service", "plan", "apply", "send", "status", "health", "progress",
    "upgrade-rules", "install-skill", "review", "inbox", "resume", "run", "mcp", "dash", "obs", "check", "kiro-profile",
]


@pytest.fixture
def team(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire(ROOT, "ceo", "Chief", "Lead.", can_hire=True)
    return made


def wire():  # type: ignore[no-untyped-def]
    from orgmcp.app import wire_cli

    return wire_cli


def test_the_program_is_the_command_line_with_the_25_commands_in_order() -> None:
    assert isinstance(wire().cli_app(), CliApp)
    session = wire().AnnouncingOrgSession(wire().os_locator(), wire().RuntimeOrgOpener(), wire().StandardOutput())
    commands = wire().commands_over(session, wire().StandardOutput(), wire().StandardTerminal(), FakeClock())
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    for command in commands:
        command.add_arguments(sub)
    assert list(sub.choices) == COMMANDS and all(callable(c.run) for c in commands)


def test_the_wiring_has_no_port_of_its_own() -> None:
    from orgmcp.app import fields_cli, wiring
    from orgmcp.app.wire_cli import register

    assert fields_cli.STEP == "D-cli" and "CliApp" in fields_cli.NOT_A_FIELD
    assert register in wiring.registrars()


def test_the_output_and_the_terminal_are_the_standard_ones_looked_up_at_each_call(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    out = wire().StandardOutput()
    out.say("one")
    out.say()
    out.write("two")
    out.warn("three")
    captured = capsys.readouterr()
    assert captured.out == "one\n\ntwo" and captured.err == "three\n"
    terminal = wire().StandardTerminal()

    class Tty(io.StringIO):
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr("sys.stdin", Tty())
    monkeypatch.setattr("sys.stdout", io.StringIO())
    assert terminal.stdout_is_tty() is False and terminal.is_interactive() is False
    monkeypatch.setattr("sys.stdout", Tty())
    assert terminal.stdout_is_tty() is True and terminal.is_interactive() is True


def test_json_is_indented_and_made_of_text(tmp_path: Path) -> None:
    dump = wire().PlainJson().dump({"at": datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc), "path": tmp_path, "tags": ("a", "b"), "set": {1}})
    assert dump == json.dumps({"at": "2026-01-15T09:00:00+00:00", "path": str(tmp_path), "tags": ["a", "b"], "set": [1]}, indent=2)


def test_the_opener_opens_an_organization_and_refuses_a_directory_that_is_none(team: Org, tmp_path: Path) -> None:
    opener = wire().RuntimeOrgOpener()
    ports = opener.open(team.root)
    assert ports.root == team.root and isinstance(ports.get(Hiring), Hiring)
    with pytest.raises(OrgError, match="not an organization"):
        opener.open(tmp_path / "nowhere")
    assert opener.prepare(tmp_path / "nowhere").root == tmp_path / "nowhere"


def test_a_provider_asks_the_organization_the_session_opened_last(team: Org) -> None:
    session = wire().AnnouncingOrgSession(wire().os_locator(), wire().RuntimeOrgOpener(), MemoryOutput())
    hiring = wire().of(session, Hiring)
    with pytest.raises(OrgError, match="no organization is open"):
        hiring()
    session.open(argparse.Namespace(root=str(team.root)))
    assert isinstance(hiring(), Hiring)


def test_the_tail_sees_the_events_written_after_it_started(team: Org) -> None:
    ports = wire().RuntimeOrgOpener().open(team.root)
    tails = wire().RuntimeEventTails(ports)
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
    assert wire().RuntimeEventTails(wire().RuntimeOrgOpener().open(root)).any() is False


def test_the_scheduler_runner_runs_the_loop_until_there_is_nothing_to_do(team: Org) -> None:
    out = MemoryOutput()
    runner = wire().LoopSchedulerRunner(out, FakeClock())
    runner.run(team.root, "kiro-cli", once=False, until_idle=False, until_done=True, max_runs=None)
    assert out.stdout == "scheduler exiting: finished: no open tasks\n"
    out.events.clear()
    runner.run(team.root, "kiro-cli", once=True, until_idle=False, until_done=False, max_runs=None)
    assert out.stdout == ""  # (one pass, nothing to run)


def test_the_launchers_of_the_other_entry_points_import_them_only_when_they_run(team: Org, monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[object] = []
    monkeypatch.setattr("orgmcp.dashboard.run_dashboard", lambda root, interval=2.0: started.append((root, interval)))
    wire().LazyDashboardRunner().run(team.root, 3.0)
    assert started == [(team.root, 3.0)]

    class Server:
        def run(self) -> None:
            started.append("served")

    monkeypatch.setattr(wire(), "mcp_server_runner", lambda: Server())
    wire().LazyMcpRunner().run()
    assert started[-1] == "served"


def test_the_plan_of_a_blueprint_is_checked_without_an_organization_against_the_defaults() -> None:
    validator, renderer = wire().PlanTime().get()
    bp = {"mission": "m", "agents": [{"name": "lead", "template": "manager"}]}
    issues = validator.validate(bp, org_exists=False)
    assert [i.path for i in issues if i.level == "error"] and "Plan for approval" in renderer.render_plan(bp, issues)
    assert wire().PlanTime().get() is not None


def test_the_snapshot_of_dash_once_comes_from_the_runtime_of_the_dashboard(team: Org) -> None:
    session = wire().AnnouncingOrgSession(wire().os_locator(), wire().RuntimeOrgOpener(), MemoryOutput())
    session.open(argparse.Namespace(root=str(team.root)))
    assert "orgmcp dash" in wire().snapshot_renderer_of(session)().render_once()


def test_nothing_but_the_run_of_a_command_imports_the_framework_of_the_server_or_of_the_screen() -> None:
    code = textwrap.dedent("""
        import sys
        from orgmcp.app import wire_cli
        wire_cli.cli_app()
        print([m for m in ("textual", "mcp.server.fastmcp", "orgmcp.dashboard", "orgmcp.server") if m in sys.modules])
    """)
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "[]"
