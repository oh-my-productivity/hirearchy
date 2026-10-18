"""The fakes of the locator: the model over a set of directories, and the one that always finds the same root."""

from __future__ import annotations

from pathlib import Path

from orgmcp.kernel.testing import DictEnvironment
from orgmcp.locator import OrgLocator
from orgmcp.locator.testing import FixedOrgLocator, MemoryOrgLocator
from orgmcp.locator.tests._red import red


def test_the_fakes_are_org_locators(tmp_path: Path) -> None:
    assert isinstance(MemoryOrgLocator(DictEnvironment()), OrgLocator)
    assert isinstance(FixedOrgLocator(tmp_path), OrgLocator)


@red
def test_the_fixed_locator_ignores_the_start_and_the_environment(tmp_path: Path) -> None:
    fixed = FixedOrgLocator(tmp_path / "org")
    assert fixed.find_root() == fixed.find_root(tmp_path / "anywhere") == tmp_path / "org"


@red
def test_the_memory_locator_follows_the_set_of_organizations(tmp_path: Path) -> None:
    organizations: set[Path] = set()
    locator = MemoryOrgLocator(DictEnvironment(cwd=tmp_path / "a" / "b"), organizations)
    organizations.add(tmp_path)
    assert locator.find_root() == tmp_path
    organizations.discard(tmp_path)
    organizations.add(tmp_path / "a")
    assert locator.find_root() == tmp_path / "a"
