"""``FsKiroState`` on a real file system: private directories, fresh scratch directories and the audit of a kiro home
(docs/design/kiro-runtime-v3.md 8.2, 8.4 and amendments A1, A8)."""

from __future__ import annotations

import json
import os
import shutil
import stat
import time
from pathlib import Path

import pytest

from hirearchy.kernel.testing import FakeClock, system_clock
from hirearchy.kiro._state import FsKiroState, planted_problem


def state(tmp_path: Path) -> FsKiroState:
    return FsKiroState(system_clock(tmp_path))


def profile(home: Path, name: str, text: str | None = None) -> Path:
    path = home / "agents" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text is not None else json.dumps({"name": name}), encoding="utf-8")
    return path


def touch(home: Path, rel: str) -> None:
    path = home / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")


# ------------------------------------------------------------------------------------------------------------- private_dir


def test_private_dir_creates_the_home_and_its_parents_with_mode_0700(tmp_path: Path) -> None:
    home = tmp_path / "a" / "b" / "home"
    state(tmp_path).private_dir(home)
    assert stat.S_IMODE(home.stat().st_mode) == 0o700


def test_private_dir_makes_an_existing_directory_private(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir(mode=0o755)
    state(tmp_path).private_dir(home)
    assert stat.S_IMODE(home.stat().st_mode) == 0o700


def test_private_dir_refuses_a_symlink_at_the_home(tmp_path: Path) -> None:
    (tmp_path / "target").mkdir()
    (tmp_path / "home").symlink_to(tmp_path / "target", target_is_directory=True)
    with pytest.raises(OSError):
        state(tmp_path).private_dir(tmp_path / "home")
    assert list((tmp_path / "target").iterdir()) == []


def test_private_dir_refuses_a_file_at_the_home(tmp_path: Path) -> None:
    (tmp_path / "home").write_text("x", encoding="utf-8")
    with pytest.raises(OSError):
        state(tmp_path).private_dir(tmp_path / "home")


# ------------------------------------------------------------------------------------------------------------------- fresh


def test_fresh_makes_an_empty_private_directory(tmp_path: Path) -> None:
    scratch = tmp_path / "cwd" / "org" / "agent"
    state(tmp_path).fresh(scratch)
    assert scratch.is_dir() and list(scratch.iterdir()) == [] and stat.S_IMODE(scratch.stat().st_mode) == 0o700


def test_fresh_removes_a_real_directory_with_content(tmp_path: Path) -> None:
    scratch = tmp_path / "cwd" / "agent"
    (scratch / "sub").mkdir(parents=True)
    (scratch / "sub" / "f").write_text("x", encoding="utf-8")
    state(tmp_path).fresh(scratch)
    assert scratch.is_dir() and list(scratch.iterdir()) == []


def test_fresh_replaces_a_symlink_without_touching_its_target(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "keep").write_text("k", encoding="utf-8")
    scratch = tmp_path / "cwd" / "agent"
    scratch.parent.mkdir()
    scratch.symlink_to(target, target_is_directory=True)
    state(tmp_path).fresh(scratch)
    assert not scratch.is_symlink() and scratch.is_dir() and list(scratch.iterdir()) == []
    assert (target / "keep").read_text(encoding="utf-8") == "k"


def test_fresh_replaces_a_file(tmp_path: Path) -> None:
    scratch = tmp_path / "cwd" / "agent"
    scratch.parent.mkdir()
    scratch.write_text("x", encoding="utf-8")
    state(tmp_path).fresh(scratch)
    assert scratch.is_dir()


def test_fresh_refuses_a_symlinked_component_between_the_state_and_the_scratch(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    (elsewhere / "agent").mkdir(parents=True)
    (elsewhere / "agent" / "keep").write_text("k", encoding="utf-8")
    (tmp_path / "state" / "kiro-cwd").mkdir(parents=True)
    (tmp_path / "state" / "kiro-cwd" / "org").symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(OSError):
        state(tmp_path).fresh(tmp_path / "state" / "kiro-cwd" / "org" / "agent")
    assert (elsewhere / "agent" / "keep").read_text(encoding="utf-8") == "k"


def test_fresh_refuses_when_rmtree_follows_symlinks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scratch = tmp_path / "cwd" / "agent"
    scratch.mkdir(parents=True)
    (scratch / "keep").write_text("k", encoding="utf-8")
    monkeypatch.setattr(shutil.rmtree, "avoids_symlink_attacks", False, raising=False)
    with pytest.raises(OSError):
        state(tmp_path).fresh(scratch)
    assert (scratch / "keep").exists()


# ----------------------------------------------------------------------------------------------------------------- planted


def test_a_clean_home_has_nothing_planted(tmp_path: Path) -> None:
    assert state(tmp_path).planted(tmp_path / "missing") == []
    (tmp_path / "home").mkdir()
    assert state(tmp_path).planted(tmp_path / "home") == []


@pytest.mark.parametrize(
    "rel",
    [
        "settings/mcp.json", "settings/permissions.yaml", "settings/permissions.yml", "skills", "steering", "hooks", "powers",
        "workflows", "workspace-roots", "AGENTS.md",
    ],
)
def test_each_blacklisted_entry_is_planted(tmp_path: Path, rel: str) -> None:
    home = tmp_path / "home"
    touch(home, rel)
    assert state(tmp_path).planted(home) == [rel]


def test_cloud_cache_is_planted(tmp_path: Path) -> None:
    home = tmp_path / "home"
    touch(home, "cloud-cache/scope/config/layer/hooks.json")
    assert state(tmp_path).planted(home) == ["cloud-cache"]


def test_a_directory_blacklist_entry_is_planted_as_a_directory(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / "skills" / "x").mkdir(parents=True)
    assert state(tmp_path).planted(home) == ["skills"]


def test_the_list_is_sorted_and_relative(tmp_path: Path) -> None:
    home = tmp_path / "home"
    for rel in ("steering", "AGENTS.md", "settings/mcp.json", "agents/x.md"):
        touch(home, rel)
    found = state(tmp_path).planted(home)
    assert found == sorted(found) == ["AGENTS.md", "agents/x.md", "settings/mcp.json", "steering"]


def test_a_subdirectory_of_agents_is_planted(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / "agents" / "sub").mkdir(parents=True)
    assert state(tmp_path).planted(home) == ["agents/sub"]


def test_a_markdown_agent_is_planted(tmp_path: Path) -> None:
    home = tmp_path / "home"
    touch(home, "agents/x.md")
    assert state(tmp_path).planted(home) == ["agents/x.md"]


def test_a_profile_with_a_capital_is_planted(tmp_path: Path) -> None:
    home = tmp_path / "home"
    profile(home, "Hirearchy-A")
    assert state(tmp_path).planted(home) == ["agents/Hirearchy-A.json"]


def test_a_profile_that_does_not_parse_is_planted(tmp_path: Path) -> None:
    home = tmp_path / "home"
    profile(home, "hirearchy-a", "{not json")
    profile(home, "hirearchy-b", "[1, 2]")
    assert state(tmp_path).planted(home) == ["agents/hirearchy-a.json", "agents/hirearchy-b.json"]


def test_a_profile_whose_name_differs_from_its_file_is_planted(tmp_path: Path) -> None:
    home = tmp_path / "home"
    profile(home, "hirearchy-a", json.dumps({"name": "hirearchy-b"}))
    assert state(tmp_path).planted(home) == ["agents/hirearchy-a.json"]


def test_a_symlinked_profile_is_planted(tmp_path: Path) -> None:
    home = tmp_path / "home"
    real = tmp_path / "real.json"
    real.write_text(json.dumps({"name": "hirearchy-a"}), encoding="utf-8")
    (home / "agents").mkdir(parents=True)
    (home / "agents" / "hirearchy-a.json").symlink_to(real)
    assert state(tmp_path).planted(home) == ["agents/hirearchy-a.json"]


def test_well_formed_profiles_and_kiros_own_entries_are_ignored(tmp_path: Path) -> None:
    home = tmp_path / "home"
    profile(home, "hirearchy-acme-123abc-read-x0a1b2c3d")
    for rel in ("enterprise-management/x", "logs/2026/kiro.log", "session-index/i", "sessions/s/state", "settings/cli.json", "settings/cli.json.lock"):
        touch(home, rel)
    assert state(tmp_path).planted(home) == []


def age(path: Path, seconds: float) -> None:
    then = time.time() - seconds
    os.utime(path, (then, then))


def test_an_old_tmp_file_in_agents_is_planted(tmp_path: Path) -> None:
    home = tmp_path / "home"
    touch(home, "agents/.tmp-ab12-hirearchy-a.json")
    age(home / "agents" / ".tmp-ab12-hirearchy-a.json", 61)
    assert state(tmp_path).planted(home) == ["agents/.tmp-ab12-hirearchy-a.json"]


def test_a_fresh_tmp_file_is_ignored(tmp_path: Path) -> None:
    home = tmp_path / "home"
    touch(home, "agents/.tmp-ab12-hirearchy-a.json")
    age(home / "agents" / ".tmp-ab12-hirearchy-a.json", 5)
    assert state(tmp_path).planted(home) == []


def test_a_tmp_directory_is_planted(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / "agents" / ".tmp-dir").mkdir(parents=True)
    assert state(tmp_path).planted(home) == ["agents/.tmp-dir"]


def test_the_age_of_a_tmp_file_is_measured_with_the_clock(tmp_path: Path) -> None:
    home = tmp_path / "home"
    touch(home, "agents/.tmp-x")
    clock = FakeClock()
    clock.t = clock.t.fromtimestamp((home / "agents" / ".tmp-x").stat().st_mtime + 59, tz=clock.t.tzinfo)
    assert FsKiroState(clock).planted(home) == []
    clock.advance(2)
    assert FsKiroState(clock).planted(home) == ["agents/.tmp-x"]


def test_agents_that_is_not_a_directory_is_planted(tmp_path: Path) -> None:
    home = tmp_path / "home"
    touch(home, "agents")
    assert state(tmp_path).planted(home) == ["agents"]


# ------------------------------------------------------------------------------------------------------- planted_problem


def test_nothing_planted_is_no_problem() -> None:
    assert planted_problem(Path("/h"), []) is None


def test_the_generic_message_names_the_home_and_the_sorted_entries() -> None:
    assert planted_problem(Path("/h"), ["settings/mcp.json", "skills"]) == (
        "the kiro home /h holds configuration kiro-cli would load into every agent: settings/mcp.json, skills; "
        "remove it (this home belongs to hirearchy)"
    )


def test_cloud_cache_takes_precedence_with_its_own_message() -> None:
    assert planted_problem(Path("/h"), ["cloud-cache", "skills"]) == (
        "the kiro home /h holds cloud-cache/, configuration kiro-cli synced for this account whose hooks, steering and powers would run "
        "in every agent: synced cloud configuration cannot be confined; this account cannot run hirearchy agents confined"
    )
