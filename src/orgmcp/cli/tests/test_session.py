"""``AnnouncingOrgSession``: which organization, when it is announced (before anything is read, mutating commands only, also when the path is no organization)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from orgmcp.cli._ports import Arguments
from orgmcp.cli.testing import MemoryOutput, MemoryOrgOpener, SessionWorld, session_world
from orgmcp.cli._session import AnnouncingOrgSession
from orgmcp.kernel import OrgError
from orgmcp.locator.testing import MemoryOrgLocator
from orgmcp.kernel.testing import DictEnvironment

pytestmark = pytest.mark.xfail(strict=True, reason="red: D-cli")


def args(root: str | None = None) -> Arguments:
    return argparse.Namespace(root=root)


@pytest.fixture
def w(tmp_path: Path) -> SessionWorld:
    return session_world(tmp_path)


def test_the_root_is_the_one_given_else_the_one_found(w: SessionWorld, tmp_path: Path) -> None:
    assert w.session.named(args(str(tmp_path / "given"))) == (tmp_path / "given").resolve()
    assert w.session.named(args()) == w.found
    assert w.session.named(args("")) == w.found
    assert w.session.named(args("~/x")) == Path("~/x").expanduser().resolve()


def test_the_root_given_is_resolved(w: SessionWorld, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert w.session.named(args("sub/../given")) == (tmp_path / "given").resolve()


def test_a_command_that_only_reads_opens_without_a_word(w: SessionWorld, tmp_path: Path) -> None:
    root = w.session.open(args(str(tmp_path / "given")))
    assert root == (tmp_path / "given").resolve() and w.out.events == [] and w.opener.opened == [root]


def test_a_command_that_changes_the_organization_says_which_one_first(w: SessionWorld, tmp_path: Path) -> None:
    journal: list[str] = []
    w.opener.events, w.out.journal = journal, journal
    root = w.session.open(args(str(tmp_path / "given")), mutating=True)
    assert w.out.stderr == f"org: {root}\n" and w.out.stdout == ""
    assert journal == [f"warn:org: {root}", f"open {root}"]  # before the organization is opened, so before anything is read


def test_the_announcement_also_comes_when_the_path_is_no_organization(w: SessionWorld, tmp_path: Path) -> None:
    journal: list[str] = []
    w.opener.events, w.out.journal = journal, journal
    nowhere = (tmp_path / "nowhere").resolve()
    with pytest.raises(OrgError, match="not an organization"):
        w.session.open(args(str(nowhere)), mutating=True)
    assert journal == [f"warn:org: {nowhere}", f"open {nowhere}"]


def test_the_organization_found_from_the_working_directory_is_the_one_announced(w: SessionWorld) -> None:
    w.session.open(args(), mutating=True)
    assert w.out.stderr == f"org: {w.found}\n"


def test_nothing_is_announced_when_no_organization_is_found(tmp_path: Path) -> None:
    out = MemoryOutput()
    locator = MemoryOrgLocator(DictEnvironment({}, tmp_path), set())
    session = AnnouncingOrgSession(locator, MemoryOrgOpener(), out)
    with pytest.raises(OrgError):
        session.open(args(), mutating=True)
    assert out.events == []


def test_present_says_whether_there_is_an_organization_and_announces_nothing(w: SessionWorld, tmp_path: Path) -> None:
    assert w.session.present(args(str(tmp_path / "given"))) is True and w.session.ports().root == (tmp_path / "given").resolve()
    assert w.session.present(args(str(tmp_path / "nowhere"))) is False and w.out.events == []


def test_present_is_false_when_none_is_found(tmp_path: Path) -> None:
    session = AnnouncingOrgSession(MemoryOrgLocator(DictEnvironment({}, tmp_path), set()), MemoryOrgOpener(), MemoryOutput())
    assert session.present(args()) is False
    with pytest.raises(OrgError, match="no organization is open"):
        session.ports()


def test_a_new_organization_is_announced_and_prepared_without_looking_for_ORG_md(w: SessionWorld, tmp_path: Path) -> None:
    root = w.session.create(str(tmp_path / "new"))
    assert root == (tmp_path / "new").resolve() and w.out.stderr == f"org: {root}\n"
    assert w.opener.prepared == [root] and w.opener.opened == [] and w.session.ports().root == root


def test_the_default_path_of_a_new_organization_is_relative_to_the_working_directory(w: SessionWorld, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert w.session.create("org") == (tmp_path / "org").resolve()


def test_ports_before_anything_was_opened_is_an_error(w: SessionWorld) -> None:
    with pytest.raises(OrgError, match="no organization is open"):
        w.session.ports()
