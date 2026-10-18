"""``GitOrgSnapshotter``: when it asks git, what it asks, and what it swallows (over the in-memory ``RecordingGit``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import OrgPaths
from orgmcp.snapshots import GitClient
from orgmcp.snapshots._git import GitOrgSnapshotter
from orgmcp.snapshots.testing import RecordingGit

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-snapshots")

ROOT = Path("/org")


def make(git: GitClient) -> GitOrgSnapshotter:
    return GitOrgSnapshotter(OrgPaths(ROOT), git)


def test_init_repository_initialises_the_organization_directory_when_git_exists_and_there_is_no_repository() -> None:
    git = RecordingGit()
    make(git).init_repository()
    assert git.calls == [("init", str(ROOT))]


def test_init_repository_asks_nothing_more_when_there_is_a_repository() -> None:
    git = RecordingGit()
    git.repositories.add(ROOT)
    make(git).init_repository()
    assert git.calls == []


def test_init_repository_does_nothing_when_git_does_not_exist() -> None:
    git = RecordingGit(available=False)
    make(git).init_repository()
    assert git.calls == [] and not git.has_repository(ROOT)


def test_commit_asks_git_to_commit_everything_with_the_message() -> None:
    git = RecordingGit()
    git.repositories.add(ROOT)
    make(git).commit("root: hired ceo")
    assert git.calls == [("commit_all", str(ROOT), "root: hired ceo")]


def test_commit_without_a_repository_does_not_ask_git() -> None:
    git = RecordingGit()
    make(git).commit("x")
    assert git.calls == []


def test_commit_swallows_a_missing_git_program() -> None:
    git = RecordingGit(available=False)
    git.repositories.add(ROOT)
    make(git).commit("x")  # git raises FileNotFoundError, an OSError


class RefusingGit(GitClient):
    """A git whose every call fails the way the operating system can make it fail."""

    def available(self) -> bool:
        return True

    def has_repository(self, root: Path) -> bool:
        return True

    def init(self, root: Path) -> None:
        raise PermissionError(13, "denied")

    def commit_all(self, root: Path, message: str) -> None:
        raise PermissionError(13, "denied")


def test_commit_swallows_an_operating_system_error() -> None:
    make(RefusingGit()).commit("x")
