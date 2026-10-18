"""``SubprocessGit`` against the real git program, in a temporary directory only."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from orgmcp.snapshots._git import SubprocessGit
from orgmcp.snapshots.testing import NO_GIT


def run(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "org").mkdir()
    return tmp_path / "org"


def test_a_program_that_does_not_exist_is_not_available() -> None:
    assert SubprocessGit(NO_GIT).available() is False


def test_has_repository_looks_for_the_git_entry_of_that_directory_only(root: Path) -> None:
    (root / "sub").mkdir()
    SubprocessGit().init(root)
    assert SubprocessGit().has_repository(root) is True
    assert SubprocessGit().has_repository(root / "sub") is False  # a directory inside a repository is not one


def test_init_is_quiet(root: Path, capfd: pytest.CaptureFixture[str]) -> None:
    SubprocessGit().init(root)
    out = capfd.readouterr()
    assert (out.out, out.err) == ("", "")


def test_commit_all_leaves_out_what_the_gitignore_names(root: Path) -> None:
    git = SubprocessGit()
    git.init(root)
    (root / ".gitignore").write_text(".runtime/events/\nruns/\n", encoding="utf-8")
    (root / ".runtime" / "events").mkdir(parents=True)
    (root / ".runtime" / "events" / "e.jsonl").write_text("{}\n", encoding="utf-8")
    (root / "runs").mkdir()
    (root / "runs" / "x.log").write_text("log\n", encoding="utf-8")
    (root / "ORG.md").write_text("org\n", encoding="utf-8")
    git.commit_all(root, "init organization")
    assert sorted(run(root, "ls-files").split()) == [".gitignore", "ORG.md"]


def test_the_identity_is_orgmcp_whatever_the_repository_configures(root: Path) -> None:
    git = SubprocessGit()
    git.init(root)
    run(root, "config", "user.name", "Somebody Else")
    run(root, "config", "user.email", "else@example.com")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    git.commit_all(root, "m")
    assert run(root, "log", "-1", "--format=%an <%ae> / %cn <%ce>").strip() == "orgmcp <orgmcp@localhost> / orgmcp <orgmcp@localhost>"


def test_a_missing_program_raises_an_os_error(root: Path) -> None:
    git = SubprocessGit(NO_GIT)
    with pytest.raises(OSError):
        git.init(root)
    with pytest.raises(OSError):
        git.commit_all(root, "m")
