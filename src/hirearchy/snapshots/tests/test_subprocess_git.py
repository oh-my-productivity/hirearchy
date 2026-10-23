"""``SubprocessGit`` against the real git program, in a temporary directory only."""

from __future__ import annotations

import os
import stat
import subprocess
import time
from pathlib import Path

import pytest

from hirearchy.snapshots._git import SubprocessGit
from hirearchy.snapshots.testing import NO_GIT


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


def test_the_identity_is_hirearchy_whatever_the_repository_configures(root: Path) -> None:
    git = SubprocessGit()
    git.init(root)
    run(root, "config", "user.name", "Somebody Else")
    run(root, "config", "user.email", "else@example.com")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    git.commit_all(root, "m")
    assert run(root, "log", "-1", "--format=%an <%ae> / %cn <%ce>").strip() == "hirearchy <hirearchy@localhost> / hirearchy <hirearchy@localhost>"


def test_a_missing_program_raises_an_os_error(root: Path) -> None:
    git = SubprocessGit(NO_GIT)
    with pytest.raises(OSError):
        git.init(root)
    with pytest.raises(OSError):
        git.commit_all(root, "m")


# ------------------------------------------------------------------------------ the read methods: how git is asked


def wrapper(tmp_path: Path, body: str) -> str:
    """An executable stand-in for git (a shell script), to see how ``SubprocessGit`` asks and what it does when git is slow."""
    script = tmp_path / "git-stand-in"
    script.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return str(script)


def logging_git(tmp_path: Path) -> tuple[SubprocessGit, Path]:
    log = tmp_path / "git-calls.log"
    return SubprocessGit(wrapper(tmp_path, f'echo "$@" >> "{log}"\nexec git "$@"\n')), log


def test_the_read_methods_run_git_with_literal_pathspecs_in_the_repository(tmp_path: Path, root: Path) -> None:
    git, log = logging_git(tmp_path)
    git.init(root)
    (root / "a*.md").write_text("a\n", encoding="utf-8")
    git.commit_all(root, "m")
    log.unlink(missing_ok=True)
    assert git.added_by(root, "a*.md") is not None
    head = git.object_id(root, "HEAD")
    assert head is not None and git.cat(root, git.object_id(root, f"{head}:a*.md") or "", 100) == b"a\n"
    calls = log.read_text(encoding="utf-8").splitlines()
    assert calls[0] == "--literal-pathspecs log --format=%H --diff-filter=A -- a*.md"
    assert all(call.startswith("--literal-pathspecs ") for call in calls)


def test_cat_asks_for_the_size_and_reads_the_blob_only_when_it_fits(tmp_path: Path, root: Path) -> None:
    git, log = logging_git(tmp_path)
    git.init(root)
    (root / "big.bin").write_bytes(b"x" * 5000)
    git.commit_all(root, "m")
    blob = git.object_id(root, "HEAD:big.bin")
    assert blob is not None
    log.unlink(missing_ok=True)
    assert git.cat(root, blob, 4999) is None
    assert [c.split()[1:] for c in log.read_text(encoding="utf-8").splitlines()] == [["cat-file", "-s", blob]]  # the blob itself was not asked for
    log.unlink()
    assert git.cat(root, blob, 5000) == b"x" * 5000
    assert [c.split()[1:] for c in log.read_text(encoding="utf-8").splitlines()] == [["cat-file", "-s", blob], ["cat-file", "blob", blob]]


def test_a_read_that_takes_longer_than_the_timeout_answers_none_in_time(tmp_path: Path, root: Path) -> None:
    git = SubprocessGit(wrapper(tmp_path, "exec sleep 5\n"), timeout=0.3)
    started = time.monotonic()
    assert (git.added_by(root, "a.md"), git.object_id(root, "HEAD"), git.cat(root, "0" * 40, 10)) == (None, None, None)
    assert time.monotonic() - started < 3.0  # three timeouts of 0.3 s, not three sleeps of 5 s


def test_the_timeout_is_2_seconds_by_default() -> None:
    assert SubprocessGit().timeout == 2.0


def test_the_read_methods_answer_none_when_the_program_is_missing(root: Path) -> None:
    git = SubprocessGit(NO_GIT)
    assert (git.added_by(root, "a.md"), git.object_id(root, "HEAD"), git.cat(root, "0" * 40, 10)) == (None, None, None)
    assert os.path.isdir(root)
