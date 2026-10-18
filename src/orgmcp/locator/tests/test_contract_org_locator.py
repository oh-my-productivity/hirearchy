"""Contract of ``OrgLocator``: the lookup over the environment and the directories, and its in-memory model."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import OrgError
from orgmcp.locator import OrgLocator
from orgmcp.locator.testing import IMPLEMENTATIONS, LocatorHarness

MESSAGE = "no organization found: set ORG_ROOT or run inside an org directory"


@pytest.fixture(params=IMPLEMENTATIONS[OrgLocator], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> LocatorHarness:
    made = cast(Callable[[Path], LocatorHarness], request.param)(tmp_path)
    assert isinstance(made.locator, OrgLocator)
    return made


def test_the_directory_itself_when_it_is_an_organization(h: LocatorHarness) -> None:
    h.make_org(h.cwd)
    assert h.locator.find_root() == h.cwd
    assert h.locator.find_root(h.cwd) == h.cwd


def test_the_nearest_organization_above(h: LocatorHarness) -> None:
    h.make_org(h.cwd.parent.parent)
    assert h.locator.find_root() == h.cwd.parent.parent
    h.make_org(h.cwd.parent)
    assert h.locator.find_root() == h.cwd.parent  # the nearest one wins


def test_an_explicit_start_is_used_instead_of_the_working_directory(h: LocatorHarness) -> None:
    elsewhere = h.cwd.parent.parent.parent / "elsewhere" / "deeper"
    elsewhere.mkdir(parents=True)
    h.make_org(h.cwd.parent)
    h.make_org(elsewhere.parent)
    assert h.locator.find_root(elsewhere) == elsewhere.parent
    assert h.locator.find_root(h.cwd) == h.cwd.parent
    assert h.locator.find_root() == h.cwd.parent


def test_ORG_ROOT_wins_and_need_not_be_an_organization(h: LocatorHarness) -> None:
    h.make_org(h.cwd)
    target = h.cwd.parent.parent / "named"
    h.set_env("ORG_ROOT", str(target))
    assert h.locator.find_root() == target
    assert h.locator.find_root(h.cwd.parent) == target


def test_ORG_ROOT_is_resolved(h: LocatorHarness) -> None:
    h.set_env("ORG_ROOT", str(h.cwd.parent / ".." / "named"))
    assert h.locator.find_root() == h.cwd.parent.parent / "named"


def test_an_empty_ORG_ROOT_is_no_ORG_ROOT(h: LocatorHarness) -> None:
    h.make_org(h.cwd.parent)
    h.set_env("ORG_ROOT", "")
    assert h.locator.find_root() == h.cwd.parent


def test_the_start_is_resolved(h: LocatorHarness) -> None:
    h.make_org(h.cwd.parent)
    assert h.locator.find_root(h.cwd / ".." / "c") == h.cwd.parent


def test_a_directory_called_org_below_the_start_is_the_last_resort(h: LocatorHarness) -> None:
    h.make_org(h.cwd / "org")
    assert h.locator.find_root() == h.cwd / "org"
    assert h.locator.find_root(h.cwd) == h.cwd / "org"


def test_an_organization_at_or_above_the_start_wins_over_the_directory_called_org(h: LocatorHarness) -> None:
    h.make_org(h.cwd / "org")
    h.make_org(h.cwd.parent)
    assert h.locator.find_root() == h.cwd.parent
    h.make_org(h.cwd)
    assert h.locator.find_root() == h.cwd


def test_only_the_start_itself_is_asked_for_a_directory_called_org(h: LocatorHarness) -> None:
    h.make_org(h.cwd.parent / "org")  # beside the working directory, not below it
    h.make_org(h.cwd / "x" / "org")  # two levels below it
    with pytest.raises(OrgError):
        h.locator.find_root()


def test_something_called_ORG_md_that_is_not_a_file_does_not_count(h: LocatorHarness) -> None:
    h.make_decoy(h.cwd)
    h.make_decoy(h.cwd / "org")
    with pytest.raises(OrgError):
        h.locator.find_root()


def test_no_organization_is_an_error_with_this_message(h: LocatorHarness) -> None:
    with pytest.raises(OrgError) as raised:
        h.locator.find_root()
    assert str(raised.value) == MESSAGE
    with pytest.raises(OrgError):
        h.locator.find_root(h.cwd.parent)
