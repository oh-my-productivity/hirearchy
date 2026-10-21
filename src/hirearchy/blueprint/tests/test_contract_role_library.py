"""Contract of ``RoleLibrary``: role templates by name; a name that is not an agent name never matches."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.blueprint import RoleLibrary
from hirearchy.blueprint.testing import IMPLEMENTATIONS, RoleHarness

from ._support import implementations, make, role


@pytest.fixture(params=implementations(IMPLEMENTATIONS[RoleLibrary]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> RoleHarness:
    made = make(request, tmp_path, RoleHarness)
    assert isinstance(made.library, RoleLibrary)
    return made


def test_a_library_without_templates_has_no_names_and_no_roles(h: RoleHarness) -> None:
    assert h.library.role_names() == []
    assert h.library.get_role("writer") is None


def test_the_names_are_sorted(h: RoleHarness) -> None:
    for name in ("writer", "analyst", "manager"):
        h.put(role(name))
    assert h.library.role_names() == ["analyst", "manager", "writer"]


def test_a_role_is_read_back_with_every_field(h: RoleHarness) -> None:
    wanted = role("fact-checker", title="Fact checker", kind="verifier", tier="strong", tools=("web_search", "web_fetch"), base_runs=3,
                  summary="Checks every claim.", body="Check each claim against its source.")
    h.put(wanted)
    assert h.library.get_role("fact-checker") == wanted


def test_a_role_without_tools_has_an_empty_tuple(h: RoleHarness) -> None:
    h.put(role("manager", kind="manager", tools=()))
    found = h.library.get_role("manager")
    assert found is not None and found.tools == ()


def test_an_unknown_role_is_none(h: RoleHarness) -> None:
    h.put(role("writer"))
    assert h.library.get_role("poet") is None


@pytest.mark.parametrize("name", ["Writer", "Bad Name", "../writer", "", "writer.md", "9lives"])
def test_a_name_that_is_not_an_agent_name_is_none_even_when_a_template_is_stored_under_it(h: RoleHarness, name: str) -> None:
    h.put(role("writer"))
    if "/" not in name and name:
        h.put(role(name))
    assert h.library.get_role(name) is None
