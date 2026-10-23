"""Contract of ``GitClient``: the real ``git`` program in a temporary directory and the in-memory ``RecordingGit``."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.snapshots import GitClient, blob_id
from hirearchy.snapshots.testing import AUTHOR, IMPLEMENTATIONS, GitHarness


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


# ------------------------------------------------------------------------------ the read methods (added_by, object_id, cat)

COMMIT_ID = 40  # sha1 repositories: the real git here is not asked for sha256 (test_api.py checks blob_id for it)


def commit(h: GitHarness, message: str, *names: str) -> str:
    """Change ``names``, commit them and return the id of the new HEAD."""
    for name in names:
        h.change(name)
    h.git.commit_all(h.root, message)
    head = h.git.object_id(h.root, "HEAD")
    assert head is not None and len(head) == COMMIT_ID
    return head


def test_added_by_gives_the_commit_that_added_a_path(h: GitHarness) -> None:
    h.git.init(h.root)
    first = commit(h, "first", "a.txt", "sub/b.txt")
    second = commit(h, "second", "a.txt", "c.txt")  # a.txt changes: it was not added again
    assert h.git.added_by(h.root, "a.txt") == first
    assert h.git.added_by(h.root, "sub/b.txt") == first
    assert h.git.added_by(h.root, "c.txt") == second
    assert h.git.added_by(h.root, "missing.txt") is None


def test_object_id_verifies_a_spec(h: GitHarness) -> None:
    h.git.init(h.root)
    first = commit(h, "first", "a.txt")
    before = h.read("a.txt")
    second = commit(h, "second", "a.txt")
    assert h.git.object_id(h.root, "HEAD") == second
    assert h.git.object_id(h.root, f"{first}:a.txt") == blob_id(before)  # the content a.txt had in the first commit
    assert h.git.object_id(h.root, f"{second}:a.txt") == blob_id(h.read("a.txt")) != blob_id(before)
    for spec in (f"{first}:missing.txt", "no-such-ref", "", "-h", "--all", f"{'0' * COMMIT_ID}:a.txt"):
        assert h.git.object_id(h.root, spec) is None, spec


def test_cat_checks_the_size_before_reading_the_blob(h: GitHarness) -> None:
    h.git.init(h.root)
    commit(h, "first", "a.txt")
    data = h.read("a.txt")
    blob = blob_id(data)
    assert h.git.cat(h.root, blob, len(data)) == data  # exactly at the limit
    assert h.git.cat(h.root, blob, len(data) - 1) is None  # one byte over: not read
    assert h.git.cat(h.root, blob, 0) is None
    for bad in ("0" * COMMIT_ID, "zz", "", "-s", "--help", "HEAD", blob[:-1]):  # not an object, or not an id
        assert h.git.cat(h.root, bad, 10_000) is None, bad


def test_read_methods_answer_none_on_a_failure_or_a_timeout(h: GitHarness) -> None:
    # no repository yet
    assert (h.git.added_by(h.root, "a.txt"), h.git.object_id(h.root, "HEAD"), h.git.cat(h.root, "0" * COMMIT_ID, 10)) == (None, None, None)
    h.git.init(h.root)
    first = commit(h, "first", "a.txt")
    blob = blob_id(h.read("a.txt"))
    assert (h.git.added_by(h.root, "a.txt"), h.git.cat(h.root, blob, 100)) == (first, h.read("a.txt"))
    h.break_repository()
    assert (h.git.added_by(h.root, "a.txt"), h.git.object_id(h.root, "HEAD"), h.git.cat(h.root, blob, 100)) == (None, None, None)


def test_a_path_with_star_and_colon_paren_is_read_literally(h: GitHarness) -> None:
    """``*`` and ``:(...)`` in an artifact path are characters, not pathspec magic (``--literal-pathspecs``)."""
    h.git.init(h.root)
    commit(h, "plain", "ab.md", "b.md", "z.md")
    star = commit(h, "star", "a*.md")
    magic = commit(h, "magic", ":(exclude)b.md")
    assert h.git.added_by(h.root, "a*.md") == star  # a glob would find ab.md, added by the first commit
    assert h.git.added_by(h.root, ":(exclude)b.md") == magic  # magic would find z.md, added by the first commit
    assert h.git.added_by(h.root, "a?.md") is None  # nothing is named that
    assert h.git.object_id(h.root, f"{star}:a*.md") == blob_id(h.read("a*.md"))
