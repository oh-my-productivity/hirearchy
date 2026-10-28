"""``is_verifier``: the one definition of a check (design 3, PC-1): the stored ``kind``, else the title of a verifier template."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.blueprint import RoleLibrary, is_verifier
from hirearchy.blueprint._roles import PackagedRoleLibrary
from hirearchy.blueprint.testing import MemoryRoleLibrary

from ._support import role

ROLES_DIR = Path(__file__).resolve().parents[2] / "roles"
SHIPPED = PackagedRoleLibrary(ROLES_DIR)


def test_kind_verifier_is_a_verifier() -> None:
    assert is_verifier({"kind": "verifier", "role": "Whatever"}, MemoryRoleLibrary())


@pytest.mark.parametrize("title", [
    "Independent Reviewer", "Independent Fact-Checker", "Code Reviewer", "Independent Data Checker", "Tester",
])
def test_without_kind_a_verifier_templates_title_is_a_verifier(title: str) -> None:
    assert is_verifier({"role": title}, SHIPPED)


@pytest.mark.parametrize("meta", [
    {"role": "Writer"}, {"role": "Manager"}, {"role": "Engineer"}, {"role": "an independent reviewer"}, {"role": ""}, {},
    {"kind": "author", "role": "Writer"}, {"kind": "manager", "role": "Manager"},
])
def test_any_other_charter_is_not_a_verifier(meta: dict[str, object]) -> None:
    assert not is_verifier(meta, SHIPPED)


def test_a_stored_kind_wins_over_the_title() -> None:
    roles: RoleLibrary = MemoryRoleLibrary([role("reviewer", title="Independent Reviewer", kind="verifier")])
    assert not is_verifier({"kind": "author", "role": "Independent Reviewer"}, roles)
    assert is_verifier({"kind": "verifier", "role": "Writer"}, roles)
    assert is_verifier({"role": "Independent Reviewer"}, roles)
