"""``PackagedSkillSource``: the wheel's ``_skill/`` first, the checkout's ``skills/hirearchy/`` second, else ``OrgError``."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import OrgError
from hirearchy.skill._source import PackagedSkillSource


def layout(tmp_path: Path) -> tuple[Path, Path, Path]:
    """(package directory, the wheel's copy, the checkout's copy) of a source tree that is also a site-packages."""
    package = tmp_path / "repo" / "src" / "hirearchy"
    package.mkdir(parents=True)
    return package, package / "_skill" / "SKILL.md", tmp_path / "repo" / "skills" / "hirearchy" / "SKILL.md"


def put(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_the_wheel_copy_is_preferred_to_the_checkout_copy(tmp_path: Path) -> None:
    package, wheel, checkout = layout(tmp_path)
    put(wheel, "wheel")
    put(checkout, "checkout")
    source = PackagedSkillSource(package)
    assert source.path() == wheel and source.read() == "wheel"


def test_the_checkout_copy_is_used_when_there_is_no_wheel_copy(tmp_path: Path) -> None:
    package, _, checkout = layout(tmp_path)
    put(checkout, "checkout")
    source = PackagedSkillSource(package)
    assert source.path() == checkout and source.read() == "checkout"


def test_a_wheel_directory_without_the_file_falls_through_to_the_checkout(tmp_path: Path) -> None:
    package, wheel, checkout = layout(tmp_path)
    wheel.mkdir(parents=True)  # SKILL.md is a directory: not a file
    put(checkout, "checkout")
    assert PackagedSkillSource(package).read() == "checkout"


def test_the_checkout_is_two_levels_above_the_package_directory(tmp_path: Path) -> None:
    package = tmp_path / "a" / "b" / "pkg"
    package.mkdir(parents=True)
    put(tmp_path / "a" / "skills" / "hirearchy" / "SKILL.md", "two up")
    put(tmp_path / "skills" / "hirearchy" / "SKILL.md", "three up")
    assert PackagedSkillSource(package).read() == "two up"


def test_the_package_directory_is_resolved_before_the_checkout_is_computed(tmp_path: Path) -> None:
    package, _, checkout = layout(tmp_path)
    put(checkout, "checkout")
    link = tmp_path / "elsewhere" / "hirearchy"
    link.parent.mkdir()
    link.symlink_to(package, target_is_directory=True)  # a symlinked package: the file is searched from where it really is
    assert PackagedSkillSource(link).read() == "checkout"


def test_nothing_found_names_the_expected_file(tmp_path: Path) -> None:
    package, _, _ = layout(tmp_path)
    source = PackagedSkillSource(package)
    with pytest.raises(OrgError, match=r"expected skills/hirearchy/SKILL\.md"):
        source.path()
    with pytest.raises(OrgError):
        source.read()


def test_the_source_does_not_look_until_it_is_asked(tmp_path: Path) -> None:
    package, _, checkout = layout(tmp_path)
    source = PackagedSkillSource(package)  # built before the file exists
    put(checkout, "late")
    assert source.read() == "late"
