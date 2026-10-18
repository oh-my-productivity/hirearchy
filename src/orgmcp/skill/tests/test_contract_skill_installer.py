"""Contract of ``SkillInstaller``: install, leave alone, refuse to overwrite; the real parts and the in-memory ones pass the same tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import OrgError
from orgmcp.skill import SkillInstaller
from orgmcp.skill.testing import IMPLEMENTATIONS, InstallerHarness

SOURCE_MISSING = "the orgmcp skill file was not found in this installation (expected skills/orgmcp/SKILL.md)"


@pytest.fixture(params=IMPLEMENTATIONS[SkillInstaller], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> InstallerHarness:
    made = cast(Callable[[Path], InstallerHarness], request.param)(tmp_path)
    assert isinstance(made.installer, SkillInstaller)
    return made


def target_of(h: InstallerHarness) -> Path:
    return h.base / "orgmcp" / "SKILL.md"


def test_a_fresh_install_copies_the_skill_and_says_so(h: InstallerHarness) -> None:
    target = target_of(h)
    assert h.installer.install_skill(h.base) == f"{target}\ninstalled the orgmcp skill"
    assert h.read_file(target) == h.packaged


def test_an_identical_file_is_left_alone(h: InstallerHarness) -> None:
    h.installer.install_skill(h.base)
    assert h.installer.install_skill(h.base) == f"{target_of(h)}\nalready installed and up to date"
    assert h.read_file(target_of(h)) == h.packaged


def test_an_identical_file_is_up_to_date_even_with_force(h: InstallerHarness) -> None:
    h.installer.install_skill(h.base)
    assert h.installer.install_skill(h.base, force=True) == f"{target_of(h)}\nalready installed and up to date"


def test_a_different_file_is_not_replaced_without_force(h: InstallerHarness) -> None:
    h.put_file(target_of(h), "my own version\n")
    with pytest.raises(OrgError) as raised:
        h.installer.install_skill(h.base)
    assert str(raised.value) == (f"{target_of(h)} exists and differs from this version of the skill; nothing was changed. "
                                 "Use --force to replace it")
    assert h.read_file(target_of(h)) == "my own version\n"


def test_a_different_file_is_replaced_with_force(h: InstallerHarness) -> None:
    h.put_file(target_of(h), "my own version\n")
    assert h.installer.install_skill(h.base, force=True) == f"{target_of(h)}\ninstalled the orgmcp skill"
    assert h.read_file(target_of(h)) == h.packaged


def test_a_target_that_is_not_a_file_is_refused_even_with_force(h: InstallerHarness) -> None:
    h.put_dir(target_of(h))
    for force in (False, True):
        with pytest.raises(OrgError) as raised:
            h.installer.install_skill(h.base, force=force)
        assert str(raised.value) == f"{target_of(h)} exists and is not a file; nothing was changed"
    assert h.read_file(target_of(h)) is None


def test_a_missing_packaged_skill_is_refused_before_anything_is_looked_at(h: InstallerHarness) -> None:
    h.lose_source()
    h.put_dir(target_of(h))  # would be an error of its own: the source error comes first
    with pytest.raises(OrgError) as raised:
        h.installer.install_skill(h.base)
    assert str(raised.value) == SOURCE_MISSING


def test_nothing_is_written_when_the_packaged_skill_is_missing(h: InstallerHarness) -> None:
    h.lose_source()
    with pytest.raises(OrgError):
        h.installer.install_skill(h.base)
    assert h.read_file(target_of(h)) is None


def test_no_destination_installs_into_the_kiro_skills_directory_of_the_home(h: InstallerHarness) -> None:
    target = h.home / ".kiro" / "skills" / "orgmcp" / "SKILL.md"
    assert h.installer.install_skill() == f"{target}\ninstalled the orgmcp skill"
    assert h.installer.install_skill(None) == f"{target}\nalready installed and up to date"
    assert h.read_file(target) == h.packaged


def test_an_empty_destination_is_no_destination(h: InstallerHarness) -> None:
    target = h.home / ".kiro" / "skills" / "orgmcp" / "SKILL.md"
    assert h.installer.install_skill("") == f"{target}\ninstalled the orgmcp skill"


def test_the_destination_may_be_a_string_or_a_path(h: InstallerHarness) -> None:
    assert h.installer.install_skill(str(h.base)).endswith("installed the orgmcp skill")
    assert h.installer.install_skill(h.base).endswith("already installed and up to date")


def test_a_home_prefix_of_the_destination_is_expanded(h: InstallerHarness) -> None:
    target = h.home / "mine" / "orgmcp" / "SKILL.md"
    assert h.installer.install_skill("~/mine") == f"{target}\ninstalled the orgmcp skill"
    assert h.read_file(target) == h.packaged


def test_the_directories_are_made(h: InstallerHarness) -> None:
    deep = h.base / "a" / "b"
    h.installer.install_skill(deep)
    assert h.read_file(deep / "orgmcp" / "SKILL.md") == h.packaged
