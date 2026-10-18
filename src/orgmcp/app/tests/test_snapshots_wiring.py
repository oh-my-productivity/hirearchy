"""The snapshot ports in the runtime, and the legacy callers (``Org.commit``, ``Org.init``, ``ignore_runtime_files``,
``ensure_ignored``) that now go through them. The observable behaviour is what it was before the step."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from orgmcp import scheduler, telemetry
from orgmcp.app import Org, wiring
from orgmcp.snapshots import GitClient, IgnoreList, OrgSnapshotter
from orgmcp.snapshots._git import GitOrgSnapshotter, SubprocessGit
from orgmcp.snapshots._ignore import FsIgnoreList
from orgmcp.snapshots.testing import AUTHOR, RecordingGit

INITIAL_GITIGNORE = ".tmp-*\nruns/\n.kiro/\n.runtime/scheduler.pid\n.runtime/events/\n"


@pytest.fixture(autouse=True)
def isolated_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")


def log(root: Path) -> list[str]:
    out = subprocess.run(["git", "log", "--reverse", "--format=%an <%ae>|%s"], cwd=root, capture_output=True, text=True).stdout
    return out.splitlines()


def test_the_runtime_has_the_three_snapshot_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.git, SubprocessGit) and isinstance(runtime.git, GitClient)
    assert isinstance(runtime.snapshotter, GitOrgSnapshotter) and isinstance(runtime.snapshotter, OrgSnapshotter)
    assert isinstance(runtime.ignore_list, FsIgnoreList) and isinstance(runtime.ignore_list, IgnoreList)


def test_opening_a_runtime_touches_nothing_of_the_snapshots(tmp_path: Path) -> None:
    wiring.open_runtime(tmp_path / "nowhere")
    assert not (tmp_path / "nowhere").exists()


def test_a_git_override_reaches_the_snapshotter(tmp_path: Path) -> None:
    git = RecordingGit()
    runtime = wiring.open_runtime(tmp_path, {GitClient: git})
    runtime.snapshotter.init_repository()
    runtime.snapshotter.commit("x")
    assert git.calls == [("init", str(tmp_path)), ("commit_all", str(tmp_path), "x")] and git.has_repository(tmp_path)


def test_org_commit_goes_through_the_snapshotter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    org = Org.init(tmp_path / "org", "m")
    git = RecordingGit()
    git.repositories.add(org.root)
    monkeypatch.setattr(org, "runtime", wiring.open_runtime(org.root, {GitClient: git}))
    org.commit("root: hired ceo")
    assert git.calls == [("commit_all", str(org.root), "root: hired ceo")]


def test_org_commit_snapshots_a_repository_and_only_a_repository(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "m")
    org.commit("first")  # nothing changed since "init organization"
    (org.root / "note.txt").write_text("n\n", encoding="utf-8")
    org.commit("root: note")
    assert log(org.root) == [f"{AUTHOR}|init organization", f"{AUTHOR}|root: note"]
    elsewhere = tmp_path / "plain"
    elsewhere.mkdir()
    (elsewhere / "ORG.md").write_text((org.root / "ORG.md").read_text(encoding="utf-8"), encoding="utf-8")
    Org(elsewhere).commit("nobody listens")
    assert not (elsewhere / ".git").exists()


def test_org_init_writes_the_gitignore_makes_the_repository_and_the_first_commit(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "fresh", "m")
    assert (org.root / ".gitignore").read_bytes() == INITIAL_GITIGNORE.encode()
    assert log(org.root) == [f"{AUTHOR}|init organization"]
    tracked = subprocess.run(["git", "ls-files"], cwd=org.root, capture_output=True, text=True).stdout.split()
    assert ".gitignore" in tracked and "ORG.md" in tracked and not any(name.startswith(".tmp-") for name in tracked)


def test_org_init_without_git_makes_no_repository_and_does_not_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    nowhere = tmp_path / "bin"
    nowhere.mkdir()
    monkeypatch.setenv("PATH", str(nowhere))
    org = Org.init(tmp_path / "fresh", "m")
    assert not (org.root / ".git").exists() and (org.root / ".gitignore").read_bytes() == INITIAL_GITIGNORE.encode()


def test_org_init_keeps_a_repository_that_is_there(tmp_path: Path) -> None:
    root = tmp_path / "again"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.name=u", "-c", "user.email=u@x", "commit", "-q", "--allow-empty", "-m", "earlier"], cwd=root, check=True)
    Org.init(root, "m")
    assert log(root)[0].endswith("|earlier") and log(root)[-1] == f"{AUTHOR}|init organization"


def test_ignore_runtime_files_adds_the_four_lines_to_any_directory(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(".tmp-*\n", encoding="utf-8")
    scheduler.ignore_runtime_files(tmp_path)
    scheduler.ignore_runtime_files(tmp_path)
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == (
        ".tmp-*\n.runtime/running.json\n.runtime/scheduler.log\n.runtime/scheduler.exit\n.runtime/events/\n"
    )


def test_ignore_runtime_files_does_nothing_for_a_directory_that_is_not_there(tmp_path: Path) -> None:
    scheduler.ignore_runtime_files(tmp_path / "nowhere")
    assert not (tmp_path / "nowhere").exists()


def test_the_first_event_of_an_organization_ignores_the_event_log(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "old", "m")
    (org.root / ".gitignore").write_text(".tmp-*\n", encoding="utf-8")
    telemetry.emit(org.root, "custom.kind")
    assert ".runtime/events/" in (org.root / ".gitignore").read_text(encoding="utf-8").split()


def test_ensure_ignored_never_raises_and_creates_nothing(tmp_path: Path) -> None:
    telemetry.ensure_ignored(tmp_path / "nowhere")
    assert not (tmp_path / "nowhere").exists()
