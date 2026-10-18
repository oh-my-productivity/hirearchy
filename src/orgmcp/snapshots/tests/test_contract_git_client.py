"""Contract of ``GitClient``: the real ``git`` program in a temporary directory and the in-memory ``RecordingGit``."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.snapshots import GitClient
from orgmcp.snapshots.testing import AUTHOR, IMPLEMENTATIONS, GitHarness

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-snapshots")


@pytest.fixture(params=IMPLEMENTATIONS[GitClient], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> GitHarness:
    made = cast(Callable[[Path], GitHarness], request.param)(tmp_path)
    assert isinstance(made.git, GitClient)
    return made


def test_git_is_available(h: GitHarness) -> None:
    assert h.git.available() is True


def test_a_directory_is_not_a_repository_until_it_is_initialised(h: GitHarness) -> None:
    assert h.git.has_repository(h.root) is False
    h.git.init(h.root)
    assert h.git.has_repository(h.root) is True


def test_a_repository_starts_without_commits(h: GitHarness) -> None:
    h.git.init(h.root)
    assert h.commits() == []


def test_initialising_twice_keeps_the_history(h: GitHarness) -> None:
    h.git.init(h.root)
    h.change("a.txt")
    h.git.commit_all(h.root, "first")
    h.git.init(h.root)
    assert h.git.has_repository(h.root) is True
    assert [c.message for c in h.commits()] == ["first"]


def test_commit_all_commits_what_changed_with_the_message_and_the_identity(h: GitHarness) -> None:
    h.git.init(h.root)
    h.change("a.txt")
    h.git.commit_all(h.root, "root: hired ceo")
    (commit,) = h.commits()
    assert (commit.message, commit.author, commit.files) == ("root: hired ceo", AUTHOR, frozenset({"a.txt"}))


def test_a_message_keeps_its_punctuation(h: GitHarness) -> None:
    message = "ceo/eng: run failed (1), 3 message(s) [runs/2026-10-18T10.log]"
    h.git.init(h.root)
    h.change("a.txt")
    h.git.commit_all(h.root, message)
    assert [c.message for c in h.commits()] == [message]


def test_commit_all_without_a_change_commits_nothing(h: GitHarness) -> None:
    h.git.init(h.root)
    h.change("a.txt")
    h.git.commit_all(h.root, "first")
    h.git.commit_all(h.root, "second")
    assert [c.message for c in h.commits()] == ["first"]


def test_each_commit_holds_only_what_changed_since_the_last(h: GitHarness) -> None:
    h.git.init(h.root)
    h.change("a.txt")
    h.change("sub/b.txt")
    h.git.commit_all(h.root, "first")
    h.change("sub/b.txt")
    h.change("c.txt")
    h.git.commit_all(h.root, "second")
    assert [(c.message, c.files) for c in h.commits()] == [
        ("first", frozenset({"a.txt", "sub/b.txt"})),
        ("second", frozenset({"sub/b.txt", "c.txt"})),
    ]


def test_commits_come_oldest_first(h: GitHarness) -> None:
    h.git.init(h.root)
    for n in range(3):
        h.change(f"f{n}.txt")
        h.git.commit_all(h.root, f"commit {n}")
    assert [c.message for c in h.commits()] == ["commit 0", "commit 1", "commit 2"]


def test_a_repository_that_git_refuses_is_not_an_error(h: GitHarness) -> None:
    h.git.init(h.root)
    h.break_repository()
    h.change("a.txt")
    h.git.commit_all(h.root, "lost")  # must not raise
