"""``GitCheckedVersions``: the team's checked version of a file, from the organization's git history and from its files (design 6.3).

Real git in a temporary organization; ``CountingHistory`` counts the questions the class asks of it."""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

import pytest

from hirearchy.app._checked_versions import GitBlobIds, GitCheckedVersions
from hirearchy.kernel import Message, OrgPaths
from hirearchy.reflection._ports import BlobIds, CheckedVersions
from hirearchy.snapshots import OrgHistory, blob_id
from hirearchy.snapshots._git import GitOrgHistory, SubprocessGit

MIB = 1024 * 1024
RESULT = "20261022T191407596413-lead-fa63"
MEMO = "lead/work/memo.md"


@pytest.fixture(autouse=True)
def isolated_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")


class CountingHistory(OrgHistory):
    """An ``OrgHistory`` that remembers what it was asked."""

    def __init__(self, inner: OrgHistory) -> None:
        self.inner = inner
        self.calls: list[tuple[str, ...]] = []

    def first_commit_with(self, path: str) -> str | None:
        self.calls.append(("first_commit_with", path))
        return self.inner.first_commit_with(path)

    def blob(self, commit: str, path: str) -> str | None:
        self.calls.append(("blob", commit, path))
        return self.inner.blob(commit, path)

    def text(self, commit: str, path: str, limit: int) -> bytes | None:
        self.calls.append(("text", commit, path, str(limit)))
        return self.inner.text(commit, path, limit)

    def head(self) -> str | None:
        self.calls.append(("head",))
        return self.inner.head()

    def asked(self, name: str) -> int:
        return sum(1 for call in self.calls if call[0] == name)


class Org:
    """A temporary organization with a repository, and the class under test over it."""

    def __init__(self, tmp_path: Path) -> None:
        self.root = (tmp_path / "org").resolve()
        self.root.mkdir()
        self.git = SubprocessGit()
        self.git.init(self.root)
        self.paths = OrgPaths(self.root)
        self.history = CountingHistory(GitOrgHistory(self.paths, self.git))
        self.versions = GitCheckedVersions(self.history, self.paths)

    def write(self, rel: str, data: bytes | str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)
        return path

    def commit(self, message: str = "run") -> str:
        self.git.commit_all(self.root, message)
        head = self.git.object_id(self.root, "HEAD")
        assert head is not None
        return head

    def result(self, sender: str = "lead", id: str = RESULT) -> Message:
        return Message(id=id, sender=sender, to="root", type="result", status="done", body="## Artifacts\n- " + MEMO)


@pytest.fixture
def org(tmp_path: Path) -> Org:
    return Org(tmp_path)


def test_it_implements_its_ports(org: Org) -> None:
    assert isinstance(org.versions, CheckedVersions) and isinstance(GitBlobIds(), BlobIds)


def test_at_result_is_the_blob_at_the_first_commit_holding_the_sent_copy(org: Org) -> None:
    org.write(MEMO, "team v1\n")
    org.write(f"lead/sent/{RESULT}.md", "the result\n")
    first = org.commit("lead: run ok")
    org.write(MEMO, "edited later\n")
    org.commit("lead: run ok")
    assert org.versions.at_result(org.result(), MEMO) == (first, blob_id(b"team v1\n"))  # the file as the team reported it, not as it is now
    org.write("ceo/eng/work/x.md", "nested\n")
    org.write(f"ceo/eng/sent/{RESULT}.md", "nested result\n")
    nested = org.commit("ceo/eng: run ok")
    assert org.versions.at_result(org.result("ceo/eng"), "ceo/eng/work/x.md") == (nested, blob_id(b"nested\n"))
    assert org.versions.at_result(org.result(), "lead/work/missing.md") is None  # a path the commit did not hold
    assert org.versions.at_result(org.result(id="20261022T000000000000-lead-0000"), MEMO) is None  # a result never committed


def test_at_result_is_memoized_and_none_answers_wait_for_head(org: Org) -> None:
    org.write(MEMO, "team v1\n")
    org.write(f"lead/sent/{RESULT}.md", "the result\n")
    org.commit("lead: run ok")
    first = org.versions.at_result(org.result(), MEMO)
    assert first is not None
    asked = len(org.history.calls)
    assert org.versions.at_result(org.result(), MEMO) == first
    assert len(org.history.calls) == asked  # an answer is for good: commits are immutable
    later = org.result(id="20261022T200000000000-lead-beef")
    assert org.versions.at_result(later, MEMO) is None  # its sent copy is not committed yet
    before = org.history.asked("first_commit_with")
    assert org.versions.at_result(later, MEMO) is None
    assert org.history.asked("first_commit_with") == before  # the same HEAD: not asked again
    org.write(f"lead/sent/{later.id}.md", "the later result\n")
    org.write(MEMO, "team v2\n")
    new_head = org.commit("lead: run ok")
    assert org.versions.at_result(later, MEMO) == (new_head, blob_id(b"team v2\n"))  # a new commit: asked again, and now it is there
    assert org.versions.at_result(later, MEMO) == (new_head, blob_id(b"team v2\n")) and org.history.asked("first_commit_with") == before + 1


def test_at_result_without_a_repository_is_none(tmp_path: Path) -> None:
    root = tmp_path / "plain"
    root.mkdir()
    paths = OrgPaths(root)
    versions = GitCheckedVersions(GitOrgHistory(paths, SubprocessGit()), paths)
    assert versions.at_result(Message(id=RESULT, sender="lead", to="root", type="result", body=""), MEMO) is None


def test_text_is_the_history_text(org: Org) -> None:
    org.write(MEMO, "team v1\n")
    first = org.commit()
    org.write(MEMO, "team v2 is longer\n")
    org.commit()
    assert org.versions.text(first, MEMO, 100) == b"team v1\n"
    assert org.versions.text(first, MEMO, 3) is None and org.versions.text(first, "nothing.md", 100) is None


def test_current_is_the_blob_id_of_the_org_file_now(org: Org) -> None:
    org.write(MEMO, "now\n")
    assert org.versions.current(MEMO, 40) == blob_id(b"now\n")
    assert org.versions.current(MEMO, 64) == blob_id(b"now\n", 64)
    (org.root / "lead" / "work" / "exact.bin").write_bytes(b"x" * (4 * MIB))
    assert org.versions.current("lead/work/exact.bin", 40) == blob_id(b"x" * (4 * MIB))


def test_current_refuses_paths_outside_the_org_links_and_large_files(org: Org, tmp_path: Path) -> None:
    org.write(MEMO, "now\n")
    outside = tmp_path / "outside.md"
    outside.write_text("TOP SECRET\n", encoding="utf-8")
    (org.root / "lead" / "work" / "evil.md").symlink_to(outside)
    (org.root / "lead" / "inside-link.md").symlink_to(org.root / MEMO)
    (org.root / "lead" / "dirlink").symlink_to(org.root / "lead" / "work", target_is_directory=True)
    (org.root / "lead" / "outside-dir").symlink_to(tmp_path, target_is_directory=True)
    (org.root / "lead" / "work" / "over.bin").write_bytes(b"x" * (4 * MIB + 1))
    os.mkfifo(org.root / "lead" / "work" / "pipe")
    refused = [
        "../outside.md", "lead/../../outside.md", f"{outside}", "/etc/passwd", "", "lead//work/memo.md", "lead/./work/memo.md", ".",  # outside, lexical
        "lead/work/evil.md", "lead/inside-link.md", "lead/dirlink/memo.md", "lead/outside-dir/outside.md",  # links, to anywhere
        "lead/work", "lead", "lead/work/missing.md", "lead/missing/memo.md", "lead/work/memo.md/x",  # not a file, not there
        "lead/work/over.bin",  # larger than 4 MiB
    ]
    for path in refused:
        assert org.versions.current(path, 40) is None, path
    result: list[str | None] = []
    worker = threading.Thread(target=lambda: result.append(org.versions.current("lead/work/pipe", 40)), daemon=True)
    worker.start()
    worker.join(5)
    assert not worker.is_alive(), "reading a FIFO blocked"
    assert result == [None]
    assert org.versions.current(MEMO, 40) == blob_id(b"now\n")  # and the good one still answers


def test_current_follows_no_link_of_the_organization_root_itself_only_resolves_it(tmp_path: Path) -> None:
    """The organization directory may itself be reached through a link (``/tmp`` on macOS): that is the user's own layout, not a component of an artifact."""
    real = tmp_path / "real-org"
    real.mkdir()
    (real / "lead" / "work").mkdir(parents=True)
    (real / MEMO).write_text("now\n", encoding="utf-8")
    via = tmp_path / "via-link"
    via.symlink_to(real, target_is_directory=True)
    versions = GitCheckedVersions(GitOrgHistory(OrgPaths(via), SubprocessGit()), OrgPaths(via))
    assert versions.current(MEMO, 40) == blob_id(b"now\n")


def test_blob_ids_are_git_blob_ids(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for data in (b"", b"hello\n", b"\x00\xff" * 1000):
        expected = subprocess.run(["git", "hash-object", "--stdin"], cwd=tmp_path, input=data, capture_output=True, check=True).stdout.decode().strip()
        assert GitBlobIds().of(data, 40) == expected == blob_id(data)
    assert GitBlobIds().of(b"x", 64) == blob_id(b"x", 64)
