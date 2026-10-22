"""``upgrade-rules install-skill review run mcp kiro-profile`` over fakes and recording launchers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hirearchy.cli._commands_ops import (
    InstallSkillCommand,
    KiroProfileCommand,
    McpCommand,
    ReviewCommand,
    RunCommand,
    UpgradeRulesCommand,
)
from hirearchy.cli.testing import RecordingMcpRunner, RecordingSchedulerRunner
from hirearchy.kernel import OrgError
from hirearchy.kiro.testing import FixedKiroPlaces, FixedReadiness
from hirearchy.review import Note

from ._fakes import FakeOffice, FakeUpkeep, new_office, new_upkeep
from ._support import Fixture, go



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
    assert f.out.stdout == "/skills/hirearchy/SKILL.md\ninstalled the hirearchy skill\n"
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


def kiro_profile(f: Fixture, upkeep: FakeUpkeep, tmp_path: Path, state: str | None = None) -> tuple[KiroProfileCommand, FixedKiroPlaces]:
    """The command over a readiness that has ``state`` as its problem and places below ``tmp_path``."""
    places = FixedKiroPlaces(tmp_path / "state")
    return KiroProfileCommand(f.session, lambda: upkeep, lambda: FixedReadiness(None, state), lambda: places, lambda: upkeep, f.out), places


def test_kiro_profile_writes_the_profile_of_this_organization(tmp_path: Path) -> None:
    f, upkeep = Fixture(tmp_path), new_upkeep()
    command, places = kiro_profile(f, upkeep, tmp_path)
    go(command, "kiro-profile", "--tools", "read,,write")
    assert f.session.calls == [("open", True)] and upkeep.last("ensure_profile") == ((["read", "write"],), {})
    server = json.dumps({"command": "hirearchy", "args": ["mcp"]})
    assert f.out.stdout == f"wrote {places.home()}/agents/hirearchy-read-write.json (mcp server: {server})\n"  # the kiro home of the organization
    go(command, "kiro-profile")
    assert upkeep.last("ensure_profile") == (([],), {})


def test_kiro_profile_names_the_organizations_home_and_not_the_users(tmp_path: Path) -> None:
    f, upkeep = Fixture(tmp_path), new_upkeep()
    command, places = kiro_profile(f, upkeep, tmp_path)
    go(command, "kiro-profile")
    assert "~/.kiro" not in f.out.stdout and f.out.stdout.startswith(f"wrote {places.home()}/agents/")


def test_kiro_profile_refuses_on_a_state_problem_and_writes_nothing(tmp_path: Path) -> None:
    f, upkeep = Fixture(tmp_path), new_upkeep()
    command, _ = kiro_profile(f, upkeep, tmp_path, "the kiro state is bad")
    with pytest.raises(OrgError, match="^the kiro state is bad$"):
        go(command, "kiro-profile", "--tools", "read")
    assert f.session.calls == [("open", True)]  # the organization is opened first, then the state is checked
    assert upkeep.names() == [] and f.out.stdout == ""  # no profile was asked for, none was written, nothing was said


def test_kiro_profile_does_not_check_the_state_of_an_organization_that_does_not_open(tmp_path: Path) -> None:
    f, upkeep = Fixture(tmp_path, exists=False), new_upkeep()
    command, _ = kiro_profile(f, upkeep, tmp_path, "the kiro state is bad")
    with pytest.raises(OrgError, match="not an organization"):
        go(command, "kiro-profile")
    assert upkeep.names() == []
