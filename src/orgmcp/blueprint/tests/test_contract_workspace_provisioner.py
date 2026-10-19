"""Contract of ``WorkspaceProvisioner``: the directories a plan asks for - made with their parents (the ones that were made are told), removed only while empty."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.blueprint import WorkspaceProvisioner
from orgmcp.blueprint.testing import IMPLEMENTATIONS, ProvisionerHarness

from ._support import implementations, make


@pytest.fixture(params=implementations(IMPLEMENTATIONS[WorkspaceProvisioner]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> ProvisionerHarness:
    made = make(request, tmp_path, ProvisionerHarness)
    assert isinstance(made.provisioner, WorkspaceProvisioner)
    return made


def test_a_directory_that_is_there_is_not_made_again(h: ProvisionerHarness) -> None:
    assert h.provisioner.ensure(h.base) == [] and h.exists(h.base)


def test_a_new_directory_and_the_parents_it_needed_are_made_the_deepest_first(h: ProvisionerHarness) -> None:
    target = h.base / "a" / "b" / "c"
    assert h.provisioner.ensure(target) == [target, target.parent, target.parent.parent]
    assert all(h.exists(p) for p in (target, target.parent, target.parent.parent))


def test_only_the_missing_part_is_told(h: ProvisionerHarness) -> None:
    h.provisioner.ensure(h.base / "a")
    assert h.provisioner.ensure(h.base / "a" / "b") == [h.base / "a" / "b"]


def test_an_empty_directory_is_removed(h: ProvisionerHarness) -> None:
    target = h.base / "empty"
    h.provisioner.ensure(target)
    assert h.provisioner.remove_if_empty(target) is True and not h.exists(target) and h.exists(h.base)


def test_a_directory_with_a_file_stays_and_is_said_not_to_have_gone(h: ProvisionerHarness) -> None:
    target = h.base / "full"
    h.provisioner.ensure(target)
    h.put_file(target)
    assert h.provisioner.remove_if_empty(target) is False and h.exists(target)


def test_a_directory_with_a_directory_in_it_stays(h: ProvisionerHarness) -> None:
    target = h.base / "outer" / "inner"
    h.provisioner.ensure(target)
    assert h.provisioner.remove_if_empty(target.parent) is False and h.exists(target)


def test_a_directory_that_is_not_there_is_not_removed(h: ProvisionerHarness) -> None:
    assert h.provisioner.remove_if_empty(h.base / "never") is False


def test_what_was_made_can_be_taken_back_in_the_order_it_is_told(h: ProvisionerHarness) -> None:
    made = h.provisioner.ensure(h.base / "x" / "y")
    assert [h.provisioner.remove_if_empty(p) for p in made] == [True, True]
    assert not h.exists(h.base / "x") and h.exists(h.base)
