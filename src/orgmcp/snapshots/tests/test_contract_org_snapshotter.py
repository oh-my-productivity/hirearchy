"""Contract of ``OrgSnapshotter``: the real one over the ``git`` program and the one over the in-memory ``RecordingGit``;
and both when the git program does not exist."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.snapshots import OrgSnapshotter
from orgmcp.snapshots.testing import AUTHOR, IMPLEMENTATIONS, WITHOUT_GIT, SnapshotHarness

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-snapshots")


def build(request: pytest.FixtureRequest, tmp_path: Path) -> SnapshotHarness:
    made = cast(Callable[[Path], SnapshotHarness], request.param)(tmp_path)
    assert isinstance(made.snapshotter, OrgSnapshotter)
    return made


@pytest.fixture(params=IMPLEMENTATIONS[OrgSnapshotter], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> SnapshotHarness:
    return build(request, tmp_path)


@pytest.fixture(params=WITHOUT_GIT, ids=lambda factory: factory.__name__)
def no_git(request: pytest.FixtureRequest, tmp_path: Path) -> SnapshotHarness:
    return build(request, tmp_path)


def test_init_repository_makes_a_repository(h: SnapshotHarness) -> None:
    assert h.has_repository() is False
    h.snapshotter.init_repository()
    assert h.has_repository() is True


def test_init_repository_leaves_an_existing_repository_alone(h: SnapshotHarness) -> None:
    h.make_repository()
    h.change("a.txt")
    h.snapshotter.commit("first")
    h.snapshotter.init_repository()
    assert [c.message for c in h.commits()] == ["first"]


def test_commit_snapshots_everything_with_the_message_and_the_identity(h: SnapshotHarness) -> None:
    h.snapshotter.init_repository()
    h.change("ORG.md")
    h.change("ceo/AGENT.md")
    h.snapshotter.commit("init organization")
    (commit,) = h.commits()
    assert (commit.message, commit.author, commit.files) == ("init organization", AUTHOR, frozenset({"ORG.md", "ceo/AGENT.md"}))


def test_commit_without_a_change_makes_no_commit(h: SnapshotHarness) -> None:
    h.snapshotter.init_repository()
    h.change("a.txt")
    h.snapshotter.commit("one")
    h.snapshotter.commit("two")
    assert [c.message for c in h.commits()] == ["one"]


def test_commit_without_a_repository_does_nothing(h: SnapshotHarness) -> None:
    h.change("a.txt")
    h.snapshotter.commit("nobody listens")
    assert h.has_repository() is False and h.commits() == []


def test_commit_works_in_a_repository_made_outside(h: SnapshotHarness) -> None:
    h.make_repository()
    h.change("a.txt")
    h.snapshotter.commit("outside")
    assert [c.message for c in h.commits()] == ["outside"]


def test_commit_swallows_a_repository_that_git_refuses(h: SnapshotHarness) -> None:
    h.snapshotter.init_repository()
    h.break_repository()
    h.change("a.txt")
    h.snapshotter.commit("lost")  # must not raise


def test_without_git_init_repository_makes_nothing(no_git: SnapshotHarness) -> None:
    no_git.snapshotter.init_repository()
    assert no_git.has_repository() is False


def test_without_git_commit_makes_no_commit_and_does_not_raise(no_git: SnapshotHarness) -> None:
    no_git.make_repository()
    no_git.change("a.txt")
    no_git.snapshotter.commit("nobody can")
    assert no_git.commits() == []


def test_without_git_commit_in_a_directory_without_a_repository_does_nothing(no_git: SnapshotHarness) -> None:
    no_git.change("a.txt")
    no_git.snapshotter.commit("nobody can")
    assert no_git.has_repository() is False
