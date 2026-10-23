"""Contract of ``OrgHistory``: ``GitOrgHistory`` over the real git program in a temporary directory, and the in-memory ``MemoryOrgHistory``."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import OrgPaths
from hirearchy.snapshots import OrgHistory, blob_id
from hirearchy.snapshots._git import GitOrgHistory
from hirearchy.snapshots.testing import IMPLEMENTATIONS, HistoryHarness, RecordingGit


@pytest.fixture(params=IMPLEMENTATIONS[OrgHistory], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> HistoryHarness:
    made = cast(Callable[[Path], HistoryHarness], request.param)(tmp_path)
    assert isinstance(made.history, OrgHistory)
    return made


def test_first_commit_with_blob_text_and_head(h: HistoryHarness) -> None:
    first = h.commit({"lead/sent/r1.md": b"one\n", "x.md": b"x\n"})
    second = h.commit({"lead/sent/r1.md": b"two\n", "b.md": b"b\n"})
    assert h.history.head() == second
    assert h.history.first_commit_with("lead/sent/r1.md") == first  # changed later, added once
    assert h.history.first_commit_with("b.md") == second
    assert h.history.first_commit_with("nothing.md") is None
    assert h.history.blob(first, "lead/sent/r1.md") == blob_id(b"one\n")
    assert h.history.blob(second, "lead/sent/r1.md") == blob_id(b"two\n")
    assert h.history.blob(first, "b.md") is None  # not there yet
    assert h.history.text(first, "lead/sent/r1.md", 100) == b"one\n"
    assert h.history.text(second, "lead/sent/r1.md", 100) == b"two\n"
    assert h.history.text(first, "b.md", 100) is None
    assert h.history.text("0" * 40, "b.md", 100) is None  # a commit that is not there


def test_no_repository_answers_none_everywhere(h: HistoryHarness) -> None:
    for commit in ("0" * 40, "f" * 64):
        assert (h.history.first_commit_with("a.md"), h.history.blob(commit, "a.md"), h.history.text(commit, "a.md", 10)) == (None, None, None)
    assert h.history.head() is None


def test_text_over_the_limit_is_none(h: HistoryHarness) -> None:
    commit = h.commit({"a.md": b"12345", "empty.md": b""})
    assert h.history.text(commit, "a.md", 5) == b"12345"
    assert h.history.text(commit, "a.md", 4) is None
    assert h.history.text(commit, "a.md", 0) is None
    assert h.history.text(commit, "empty.md", 0) == b""


BAD_PATHS = ["", "/abs.md", "../x.md", "a/../x.md", "a//b.md", "a/./b.md", "./a.md", "a/", "a/b.md/", "-x.md", ":x.md", "a:b.md", "a^b.md", "a~b.md", "a@{b.md", "a\\b.md", "a\0b.md"]
BAD_COMMITS = ["", "abc", "g" * 40, "A" * 40, "0" * 39, "0" * 41, "f" * 63, "f" * 65, "HEAD", "main", "-h", "HEAD:a.md"]


def test_invalid_paths_and_commits_answer_none(h: HistoryHarness) -> None:
    commit = h.commit({"a.md": b"a\n"})
    for path in BAD_PATHS:
        assert (h.history.first_commit_with(path), h.history.blob(commit, path), h.history.text(commit, path, 100)) == (None, None, None), path
    for bad in BAD_COMMITS:
        assert (h.history.blob(bad, "a.md"), h.history.text(bad, "a.md", 100)) == (None, None), bad
    assert h.history.blob(commit, "a.md") == blob_id(b"a\n")  # and the good ones still answer


def test_invalid_paths_and_commits_run_no_git(tmp_path: Path) -> None:
    root = tmp_path / "org"
    root.mkdir()
    git = RecordingGit()
    git.init(root)
    git.touch(root, "a.md", b"a\n")
    git.commit_all(root, "first")
    commit = git.object_id(root, "HEAD")
    assert commit is not None
    history = GitOrgHistory(OrgPaths(root), git)
    git.reads.clear()
    for path in BAD_PATHS:
        history.first_commit_with(path)
        history.blob(commit, path)
        history.text(commit, path, 100)
    for bad in BAD_COMMITS:
        history.blob(bad, "a.md")
        history.text(bad, "a.md", 100)
    assert git.reads == []  # not one git call for an input that cannot be a path or a commit
    assert history.first_commit_with("a.md") == commit and git.reads == [("added_by", str(root), "a.md")]


def test_no_repository_runs_no_git(tmp_path: Path) -> None:
    root = tmp_path / "org"
    root.mkdir()
    git = RecordingGit()
    history = GitOrgHistory(OrgPaths(root), git)
    assert (history.head(), history.first_commit_with("a.md"), history.blob("0" * 40, "a.md"), history.text("0" * 40, "a.md", 1)) == (None,) * 4
    assert git.reads == []
