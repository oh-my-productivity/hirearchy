"""``upgrade-rules install-skill review run mcp kiro-profile`` over fakes and recording launchers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orgmcp.cli._commands_ops import (
    InstallSkillCommand,
    KiroProfileCommand,
    McpCommand,
    ReviewCommand,
    RunCommand,
    UpgradeRulesCommand,
)
from orgmcp.cli.testing import RecordingMcpRunner, RecordingSchedulerRunner
from orgmcp.kernel import OrgError
from orgmcp.review import Note

from ._fakes import FakeOffice, FakeUpkeep, new_office, new_upkeep
from ._support import Fixture, go

pytestmark = pytest.mark.xfail(strict=True, reason="red: D-cli")


def test_upgrade_rules_announces_only_when_it_writes(tmp_path: Path) -> None:
    f, upkeep = Fixture(tmp_path), new_upkeep()
    command = UpgradeRulesCommand(f.session, lambda: upkeep, f.out)
    go(command, "upgrade-rules")
    go(command, "upgrade-rules", "--dry-run")
    assert f.session.calls == [("open", True), ("open", False)]
    assert [args for _, args, _ in upkeep.calls] == [(False,), (True,)]
    assert f.out.stdout.count("\n") >= 2 and "would rewrite" in f.out.stdout


def test_install_skill_needs_no_organization(tmp_path: Path) -> None:
    f, upkeep = Fixture(tmp_path), new_upkeep()
    go(InstallSkillCommand(upkeep, f.out), "install-skill", "--dest", "/skills", "--force")
    assert upkeep.last("install_skill") == (("/skills", True), {}) and f.session.calls == []
    assert f.out.stdout == "/skills/orgmcp/SKILL.md\ninstalled the orgmcp skill\n"
    go(InstallSkillCommand(upkeep, f.out), "install-skill")
    assert upkeep.last("install_skill") == ((None, False), {})


def test_a_review_that_sent_notes_is_snapshotted(tmp_path: Path) -> None:
    f, upkeep, office = Fixture(tmp_path), new_upkeep(), new_office()
    upkeep.notes = [Note("root", "Flagged", "ceo is stuck")]
    go(ReviewCommand(f.session, lambda: upkeep, lambda: office, f.out), "review")
    assert f.session.calls == [("open", True)] and upkeep.last("review") == ((None, False), {})
    assert office.last("commit") == (("root: health review",), {})
    assert f.out.stdout.startswith("1 flagged agent(s); sent 1 note(s)\n")


def test_a_review_with_nothing_to_send_or_a_dry_run_is_not_snapshotted(tmp_path: Path) -> None:
    f, upkeep, office = Fixture(tmp_path), new_upkeep(), new_office()
    command = ReviewCommand(f.session, lambda: upkeep, lambda: office, f.out)
    go(command, "review")
    upkeep.notes = [Note("root", "Flagged", "ceo is stuck")]
    go(command, "review", "--dry-run")
    assert office.calls == [] and f.session.calls == [("open", True), ("open", False)]
    assert f.out.stdout.splitlines()[0] == "0 flagged agent(s); nothing to send"
    assert "would send 1 note(s)" in f.out.stdout


def test_run_announces_then_starts_the_scheduler_in_the_mode_the_flags_say(tmp_path: Path) -> None:
    f, runner = Fixture(tmp_path), RecordingSchedulerRunner()
    command = RunCommand(f.session, runner)
    go(command, "run", "--once", "--max-runs", "3", "--kiro", "my-kiro")
    go(command, "run", "--until-idle")
    go(command, "run", "--until-done")
    go(command, "run")
    root = tmp_path / "org"
    assert runner.runs == [
        (root, "my-kiro", True, False, False, 3), (root, "kiro-cli", False, True, False, None),
        (root, "kiro-cli", False, False, True, None), (root, "kiro-cli", False, False, False, None),
    ]
    assert f.session.calls == [("open", True)] * 4


def test_until_done_and_once_are_refused_after_the_announcement(tmp_path: Path) -> None:
    f, runner = Fixture(tmp_path), RecordingSchedulerRunner()
    with pytest.raises(OrgError, match="--until-done and --once are different modes: use one of them"):
        go(RunCommand(f.session, runner), "run", "--until-done", "--once")
    assert f.session.calls == [("open", True)] and runner.runs == []


def test_run_in_a_directory_that_is_no_organization_announces_and_fails(tmp_path: Path) -> None:
    f, runner = Fixture(tmp_path, exists=False), RecordingSchedulerRunner()
    with pytest.raises(OrgError, match="not an organization"):
        go(RunCommand(f.session, runner), "run", "--once")
    assert runner.runs == []


def test_mcp_serves_without_opening_an_organization(tmp_path: Path) -> None:
    server = RecordingMcpRunner()
    go(McpCommand(server), "mcp")
    assert server.runs == 1


def test_kiro_profile_writes_the_profile_of_this_organization(tmp_path: Path) -> None:
    f, upkeep = Fixture(tmp_path), new_upkeep()
    go(KiroProfileCommand(f.session, lambda: upkeep, lambda: upkeep, f.out), "kiro-profile", "--tools", "read,,write")
    assert f.session.calls == [("open", True)] and upkeep.last("ensure_profile") == ((["read", "write"],), {})
    assert f.out.stdout == f"wrote ~/.kiro/agents/orgmcp-read-write.json (mcp server: {json.dumps({'command': 'orgmcp', 'args': ['mcp']})})\n"
    go(KiroProfileCommand(f.session, lambda: upkeep, lambda: upkeep, f.out), "kiro-profile")
    assert upkeep.last("ensure_profile") == (([],), {})
