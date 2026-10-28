"""Contract of ``OrgHistory``: ``GitOrgHistory`` over the real git program in a temporary directory, and the in-memory ``MemoryOrgHistory``."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import OrgPaths
from hirearchy.snapshots import Change, OrgHistory, blob_id
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


# ------------------------------------------------------------------------------ subject (the first line of a commit's message)


def test_subject_is_the_first_line_of_the_commit_message(h: HistoryHarness) -> None:
    first = h.commit({"a.md": b"1\n"}, message="root: applied extension 0123456789ab")
    second = h.commit({"a.md": b"2\n"}, message="ceo: edited a charter\n\nA body that is not the subject.\nNor this line.")
    assert h.history.subject(first) == "root: applied extension 0123456789ab"
    assert h.history.subject(second) == "ceo: edited a charter"
    assert h.history.subject(h.history.head() or "") == "ceo: edited a charter"


def test_subject_is_none_for_an_invalid_commit_or_without_a_repository(h: HistoryHarness) -> None:
    assert h.history.subject("0" * 40) is None  # no repository yet
    commit = h.commit({"a.md": b"a\n"}, message="first")
    for bad in BAD_COMMITS:
        assert h.history.subject(bad) is None, bad
    assert h.history.subject("0" * 40) is None  # well formed, but no such commit
    assert h.history.subject(blob_id(b"a\n")) is None  # an object that is no commit
    assert h.history.subject(commit) == "first"  # and the good one still answers


def test_subject_runs_no_git_for_an_input_that_cannot_be_a_commit(tmp_path: Path) -> None:
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
    for bad in BAD_COMMITS:
        assert history.subject(bad) is None
    assert git.reads == []
    assert history.subject(commit) == "first" and [read[0] for read in git.reads] == ["cat"]


# ------------------------------------------------------------------------------ changes (the commits that changed some paths)


def test_changes_list_the_commits_that_changed_the_paths_newest_first(h: HistoryHarness) -> None:
    first = h.commit({"a.md": b"1\n", "b.md": b"1\n", "c.md": b"1\n"})
    second = h.commit({"a.md": b"2\n", "c.md": b"2\n"})
    found = h.history.changes(["a.md", "b.md"], 40)
    assert found is not None
    assert [(c.commit, c.path) for c in found] == [(second, "a.md"), (first, "a.md"), (first, "b.md")]
    assert all(c.when.utcoffset() is not None for c in found)
    limited = h.history.changes(["a.md", "b.md"], 1)
    assert limited is not None and [(c.commit, c.path) for c in limited] == [(second, "a.md")]  # the limit counts commits
    assert h.history.changes(["nothing.md"], 40) == []  # a repository that never changed it


def test_changes_is_none_without_a_repository_or_git(h: HistoryHarness, tmp_path: Path) -> None:
    assert h.history.changes(["a.md"], 40) is None  # no repository yet
    root = tmp_path / "no-git"
    root.mkdir()
    git = RecordingGit(available=False)
    git.repositories.add(root)  # a repository, but no git program to ask
    assert GitOrgHistory(OrgPaths(root), git).changes(["a.md"], 40) is None
    plain = RecordingGit()
    assert GitOrgHistory(OrgPaths(root), plain).changes(["a.md"], 40) is None and plain.reads == []  # not a repository: git is not asked


def at(shift: int = 0) -> str:
    return (datetime(2026, 10, 22, 19, 12, 45, tzinfo=timezone(timedelta(hours=1))) + timedelta(minutes=shift)).isoformat()


class CannedLog(RecordingGit):
    """A repository whose ``log`` answers fixed bytes: what git can print that a real small repository cannot (a sha256 id, a bad record)."""

    def __init__(self, answer: bytes) -> None:
        super().__init__()
        self.answer = answer

    def log(self, root: Path, paths: Sequence[str], limit: int) -> bytes | None:
        return self.answer


def canned(tmp_path: Path, answer: bytes) -> GitOrgHistory:
    root = tmp_path / "org"
    root.mkdir()
    git = CannedLog(answer)
    git.repositories.add(root)
    return GitOrgHistory(OrgPaths(root), git)


SHA1, SHA256, OTHER = "a" * 40, "b" * 64, "c" * 40


def test_changes_parses_sha1_and_sha256_commits(tmp_path: Path) -> None:
    answer = f"\0{SHA1}\t{at()}\nORG.md\nlead/AGENT.md\n\n\0{SHA256}\t{at(-5)}\nlead/AGENT.md\n\n".encode()
    assert canned(tmp_path, answer).changes(["ORG.md", "lead/AGENT.md"], 40) == [
        Change(SHA1, datetime.fromisoformat(at()), "ORG.md"),
        Change(SHA1, datetime.fromisoformat(at()), "lead/AGENT.md"),
        Change(SHA256, datetime.fromisoformat(at(-5)), "lead/AGENT.md"),
    ]


def test_changes_skip_a_record_that_does_not_parse(tmp_path: Path) -> None:
    answer = (
        f"\0{SHA1}\t{at()}\nORG.md\n\n"
        f"\0not-an-id\t{at(-1)}\nORG.md\n\n"  # the id is no object id
        f"\0{OTHER.upper()}\t{at(-2)}\nORG.md\n\n"  # upper case is none
        f"\0{OTHER}\tyesterday\nORG.md\n\n"  # the time is none
        f"\0{OTHER}{at(-3)}\nORG.md\n\n"  # no tab
        f"\0\xff\xfe\nORG.md\n\n"  # not even text
        f"\0{SHA256}\t{at(-4)}\nORG.md\n\n"
    ).encode("latin-1")
    found = canned(tmp_path, answer).changes(["ORG.md"], 40)
    assert found is not None and [c.commit for c in found] == [SHA1, SHA256]


def test_changes_keep_only_the_asked_paths(tmp_path: Path) -> None:
    answer = f"\0{SHA1}\t{at()}\nlead/AGENT.md\nlead/AGENT.md.bak\nlead/sub/AGENT.md\nother.md\n\n".encode()
    found = canned(tmp_path, answer).changes(["lead/AGENT.md", "ORG.md"], 40)
    assert found == [Change(SHA1, datetime.fromisoformat(at()), "lead/AGENT.md")]


def test_changes_drop_paths_that_fail_is_history_path(tmp_path: Path) -> None:
    root = tmp_path / "org"
    root.mkdir()
    git = RecordingGit()
    git.init(root)
    git.touch(root, "ORG.md", b"x\n")
    git.commit_all(root, "first")
    git.reads.clear()
    history = GitOrgHistory(OrgPaths(root), git)
    found = history.changes(["ORG.md", "../x.md", "-y", "a:b.md", "", "a//b.md"], 40)
    assert found is not None and [c.path for c in found] == ["ORG.md"]
    assert git.reads == [("log", str(root), "40", "ORG.md")]  # only the path that can be asked
    git.reads.clear()
    assert history.changes(["../x.md", "-y"], 40) == [] and git.reads == []  # nothing left to ask: git is not run
