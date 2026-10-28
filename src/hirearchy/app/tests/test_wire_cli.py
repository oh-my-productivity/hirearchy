"""``wire_cli``: the command line over a real organization - the 27 commands in the order of the parser, the session that opens the runtime, the process's own
output and terminal, the tail of the event files, the scheduler's loop and the other entry points behind their ports, the plan before there is an organization."""

from __future__ import annotations

import argparse
import io
import json
import os
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
from hirearchy.daemon import REFUSED_START, SchedulerState, SchedulerStatus
from hirearchy.daemon.testing import FakeSchedulerStatus
from hirearchy.dashboard.testing import FakeDashboardLauncher
from hirearchy.hierarchy import Hiring
from hirearchy.kernel import ROOT, OrgError
from hirearchy.kernel.testing import FakeClock
from hirearchy.kiro import RuntimeReadiness
from hirearchy.kiro.testing import FixedReadiness
from hirearchy.snapshots import RUNTIME_IGNORE_LINES


COMMANDS = [
    "init", "hire", "task", "services", "define-service", "request", "feedback", "acknowledge-playbook", "retire-service", "plan", "apply", "send", "status", "health",
    "progress", "quality", "upgrade-rules", "install-skill", "review", "inbox", "resume", "run", "mcp", "dash", "obs", "check", "kiro-profile",
]


@pytest.fixture
def team(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire(ROOT, "ceo", "Chief", "Lead.", can_hire=True)
    return made


def test_the_program_is_the_command_line_with_the_27_commands_in_order() -> None:
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
    with wiring.overriding({RuntimeReadiness: FixedReadiness(None)}):
        runner.run(team.root, "kiro-cli", once=False, until_idle=False, until_done=True, max_runs=None)
        assert out.stdout == "scheduler exiting: finished: no open tasks\n"
        out.events.clear()
        runner.run(team.root, "kiro-cli", once=True, until_idle=False, until_done=False, max_runs=None)
        assert out.stdout == ""  # (one pass, nothing to run)
    stub_log = Path(os.environ["KIRO_STUB_LOG"])
    assert not stub_log.exists() or "--version" not in stub_log.read_text(encoding="utf-8").splitlines()  # no readiness call


def tree_of(root: Path) -> dict[str, bytes]:
    """Every file of the organization (not the git objects), by relative path."""
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.relative_to(root).parts}


def refuse(team: Org, problem: str = "no key", *, once: bool = False, max_runs: int | None = None, status: SchedulerStatus | None = None) -> None:
    """Start the scheduler of ``team`` in a world where kiro-cli is not ready (``problem``) and let the refusal propagate."""
    overrides: dict[type, object] = {RuntimeReadiness: FixedReadiness(problem)}
    if status is not None:
        overrides[SchedulerStatus] = status
    with wiring.overriding(overrides):
        wire_cli.LoopSchedulerRunner(MemoryOutput(), FakeClock()).run(team.root, "kiro-cli", once=once, until_idle=False, until_done=True, max_runs=max_runs)


def test_a_refused_start_raises_and_writes_only_the_marker(team: Org) -> None:
    (team.root / ".gitignore").write_text("runs/\n", encoding="utf-8")  # (a repository that does not know the runtime files yet)
    before = tree_of(team.root)
    with pytest.raises(OrgError, match="^kiro-cli is not ready, no run was started: no key$"):
        refuse(team)
    after = tree_of(team.root)
    assert (team.root / ".runtime" / "scheduler.exit").read_text(encoding="utf-8") == f"{REFUSED_START}kiro-cli is not ready: no key\n"
    assert set(after) - set(before) == {".runtime/scheduler.exit"} and set(before) <= set(after)
    assert sorted(k for k in before if after[k] != before[k]) == [".gitignore"]  # the runtime files are ignored by the snapshots, as a claim would do
    assert set(RUNTIME_IGNORE_LINES) <= set((team.root / ".gitignore").read_text(encoding="utf-8").splitlines())


def test_a_refused_start_emits_no_event_and_starts_no_run(team: Org) -> None:
    events = wiring.open_runtime(team.root).event_reader.files()
    with pytest.raises(OrgError):
        refuse(team)
    assert wiring.open_runtime(team.root).event_reader.files() == events
    assert not (team.root / ".runtime" / "scheduler.pid").exists() and not (team.root / ".runtime" / "running.json").exists()


def test_with_a_live_scheduler_no_marker_is_written(team: Org) -> None:
    status = FakeSchedulerStatus(SchedulerState("running", 4242, "2026-10-18 10:00:00Z"))
    with pytest.raises(OrgError, match="no run was started: no key"):
        refuse(team, status=status)
    assert not (team.root / ".runtime" / "scheduler.exit").exists()  # the status of the scheduler that is alive must win


def test_status_names_the_refusal_while_root_has_an_open_task(team: Org, capsys: pytest.CaptureFixture[str]) -> None:
    team.delegate(ROOT, "ceo", "Ship it", "goal", "accept", budget=5)
    with pytest.raises(OrgError):
        refuse(team)
    wire_cli.run_cli(["--root", str(team.root), "status"])
    assert capsys.readouterr().out.rstrip().endswith("scheduler: stopped (refused to start: kiro-cli is not ready: no key)")


@pytest.mark.parametrize("once", [False, True])
def test_readiness_is_checked_first_also_with_max_runs_0(team: Org, once: bool) -> None:
    with pytest.raises(OrgError, match="no run was started: kiro-cli cannot run"):
        refuse(team, "kiro-cli cannot run", once=once, max_runs=0)
    assert (team.root / ".runtime" / "scheduler.exit").read_text(encoding="utf-8").startswith(REFUSED_START)


def test_a_ready_kiro_cli_starts_the_loop_and_leaves_no_marker(team: Org) -> None:
    with wiring.overriding({RuntimeReadiness: FixedReadiness(None)}):
        out = MemoryOutput()
        wire_cli.LoopSchedulerRunner(out, FakeClock()).run(team.root, "kiro-cli", once=False, until_idle=False, until_done=True, max_runs=None)
    assert out.stdout == "scheduler exiting: finished: no open tasks\n"


def test_the_readiness_is_asked_for_the_binary_of_the_command(team: Org) -> None:
    asked: list[str] = []

    class Spy(FixedReadiness):
        def check(self, kiro_bin: str) -> str | None:
            asked.append(kiro_bin)
            return super().check(kiro_bin)

    with wiring.overriding({RuntimeReadiness: Spy(None)}):
        wire_cli.LoopSchedulerRunner(MemoryOutput(), FakeClock()).run(team.root, "my-kiro", once=True, until_idle=False, until_done=False, max_runs=0)
    assert asked == ["my-kiro"]


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


def test_the_request_command_prints_the_step_of_the_runtime(team: Org, capsys: pytest.CaptureFixture[str]) -> None:
    """``RequestCommand`` gets the runtime's ``ServiceSteps``: a rework of an open request prints the step of the real organization. D-E6-2 (B2) changed
    this case on purpose: it is the CLI's end-to-end case of B's second part, where the team still holds the 4 runs of the open request (0a.3 printed
    the top-up for 4 more runs). D-E7-2 A1 (14 Rule A1, item 8) changed it again: contract 4 with none used leaves nothing for the rework, so it is the
    default with nothing left, and the rework's 1 run plus the 4 held cover the round of 5, but that 1 run is beyond the user's approval: the user is asked
    for it. The step is the whole top-up with HELD in ``{left}``, so the two negative assertions (no ``This rework has``, no ``Ask the
    user now``) are gone: they pinned the HELD-only step."""
    team.hire("ceo", "eng", "Engineer", "Build things.")
    team.hire("ceo", "qa", "Tester", "Test things.")
    team.define_service(
        ROOT, "ceo", "brief", description="A brief.", inputs=[{"name": "topic", "description": "what", "required": True}], acceptance=["Short"],
        deliverable={"description": "one file"}, budget=4,
    )
    first = team.request(ROOT, "brief", {"topic": "ai"})  # 4 runs handed down, none used yet: all still held
    wire_cli.run_cli(["--root", str(team.root), "request", "brief", "--input", "topic=ai", "--revises", first.id])
    out = capsys.readouterr().out
    held = f"The team still holds 4 of the user's runs for {first.id}; the rework can use them."
    assert "budget 1)" in out and (
        "This rework has 1 run(s), and a rework of this team needs about 5 (1, plus 2 for each agent below ceo). "
        f"{held} Nothing else was left of the runs the user approved for this case when this rework was sent: its own run is beyond them, and the ask "
        "includes it. Ask the user now for 1 more run(s), with that number; on yes, grant 1: send(to=\"ceo\", budget=1, body=<why>) "
        "(CLI: hirearchy send ceo \"<why>\" --budget 1)."
    ) in out

