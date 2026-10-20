"""The fakes of the package: what a consumer's test can rely on (the contract suites prove they behave like the real ones)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.snapshots.testing import AUTHOR, GitCommit, MemoryIgnoreList, RecordingGit

ROOT = Path("/org")


def test_every_call_is_recorded_in_order() -> None:
    git = RecordingGit()
    git.init(ROOT)
    git.touch(ROOT, "a")
    git.commit_all(ROOT, "m")
    assert git.calls == [("init", str(ROOT)), ("commit_all", str(ROOT), "m")]


def test_repositories_are_independent() -> None:
    git = RecordingGit()
    other = Path("/other")
    git.init(ROOT)
    git.init(other)
    git.touch(ROOT, "a")
    git.commit_all(other, "nothing here")
    git.commit_all(ROOT, "here")
    assert [c.message for c in git.commits[ROOT]] == ["here"] and git.commits[other] == []


def test_a_commit_records_the_files_and_the_identity() -> None:
    git = RecordingGit()
    git.init(ROOT)
    git.touch(ROOT, "x/y")
    git.commit_all(ROOT, "m")
    assert git.commits[ROOT] == [GitCommit("m", AUTHOR, frozenset({"x/y"}))]


def test_without_git_the_calls_raise_like_a_missing_program() -> None:
    git = RecordingGit(available=False)
    assert git.available() is False
    with pytest.raises(FileNotFoundError):
        git.init(ROOT)
    with pytest.raises(FileNotFoundError):
        git.commit_all(ROOT, "m")


def test_memory_ignore_list_works_over_one_text() -> None:
    ignore = MemoryIgnoreList("a\n")
    ignore.ensure(["b"])
    assert ignore.text == "a\nb\n"
