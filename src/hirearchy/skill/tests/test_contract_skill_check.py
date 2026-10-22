"""Contract of ``SkillCheck``: the installed copy is named when it exists and differs from the packaged skill, and never otherwise."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.skill import SkillCheck
from hirearchy.skill.testing import IMPLEMENTATIONS, InstallerHarness


@pytest.fixture(params=IMPLEMENTATIONS[SkillCheck], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> InstallerHarness:
    made = cast(Callable[[Path], InstallerHarness], request.param)(tmp_path)
    assert isinstance(made.installer, SkillCheck)
    return made


def check_of(h: InstallerHarness) -> SkillCheck:
    return cast(SkillCheck, h.installer)


def default_target(h: InstallerHarness) -> Path:
    return h.home / ".kiro" / "skills" / "hirearchy" / "SKILL.md"


def test_nothing_installed_is_not_stale(h: InstallerHarness) -> None:
    assert check_of(h).stale() is None
    assert check_of(h).stale(h.base) is None


def test_an_identical_copy_is_not_stale(h: InstallerHarness) -> None:
    h.put_file(default_target(h), h.packaged)
    assert check_of(h).stale() is None


def test_a_different_copy_is_stale_and_named(h: InstallerHarness) -> None:
    h.put_file(default_target(h), "an older version\n")
    assert check_of(h).stale() == default_target(h)


def test_a_target_that_is_a_directory_is_not_stale(h: InstallerHarness) -> None:
    h.put_dir(default_target(h))
    assert check_of(h).stale() is None


def test_a_missing_packaged_skill_is_not_stale(h: InstallerHarness) -> None:
    h.put_file(default_target(h), "an older version\n")
    h.lose_source()
    assert check_of(h).stale() is None


def test_a_given_destination_is_the_one_looked_at(h: InstallerHarness) -> None:
    target = h.base / "hirearchy" / "SKILL.md"
    h.put_file(target, "an older version\n")
    assert check_of(h).stale(h.base) == target
    assert check_of(h).stale() is None  # the default destination holds nothing
    h.put_file(target, h.packaged)
    assert check_of(h).stale(h.base) is None


def test_the_check_writes_nothing(h: InstallerHarness) -> None:
    h.put_file(default_target(h), "an older version\n")
    check_of(h).stale()
    assert h.read_file(default_target(h)) == "an older version\n"
