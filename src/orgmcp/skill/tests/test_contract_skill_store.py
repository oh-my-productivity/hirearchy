"""Contract of ``SkillStore``: one skills directory, the target ``<dest>/orgmcp/SKILL.md`` in it."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import OrgError
from orgmcp.skill import SkillStore
from orgmcp.skill.testing import IMPLEMENTATIONS, StoreHarness


@pytest.fixture(params=IMPLEMENTATIONS[SkillStore], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> StoreHarness:
    made = cast(Callable[[Path], StoreHarness], request.param)(tmp_path)
    assert isinstance(made.store, SkillStore)
    return made


def test_the_target_is_orgmcp_skill_md_in_the_directory(h: StoreHarness) -> None:
    assert h.store.target(h.base) == h.base / "orgmcp" / "SKILL.md"


def test_no_directory_means_the_kiro_skills_directory_of_the_home(h: StoreHarness) -> None:
    assert h.store.target(None) == h.home / ".kiro" / "skills" / "orgmcp" / "SKILL.md"


def test_a_home_prefix_is_expanded_to_the_home_directory(h: StoreHarness) -> None:
    assert h.store.target(Path("~") / "mine") == h.home / "mine" / "orgmcp" / "SKILL.md"


def test_the_directory_is_resolved(h: StoreHarness) -> None:
    assert h.store.target(h.base / "a" / ".." / "b") == h.base / "b" / "orgmcp" / "SKILL.md"


def test_nothing_installed_reads_as_none(h: StoreHarness) -> None:
    assert h.store.read_existing(h.base) is None
    assert h.store.read_existing(None) is None


def test_a_written_text_is_read_back_and_the_target_is_returned(h: StoreHarness) -> None:
    returned = h.store.write(h.base, "naïve ✓\nsecond\n")
    target = h.base / "orgmcp" / "SKILL.md"
    assert returned == str(target)
    assert h.read_file(target) == "naïve ✓\nsecond\n"
    assert h.store.read_existing(h.base) == "naïve ✓\nsecond\n"


def test_writing_makes_the_directories_and_replaces_a_text(h: StoreHarness) -> None:
    deep = h.base / "x" / "y"
    h.store.write(deep, "one")
    h.store.write(deep, "two")
    assert h.store.read_existing(deep) == "two"
    assert h.read_file(deep / "orgmcp" / "SKILL.md") == "two"


def test_the_default_directory_is_written_below_the_home(h: StoreHarness) -> None:
    assert h.store.write(None, "text") == str(h.home / ".kiro" / "skills" / "orgmcp" / "SKILL.md")
    assert h.read_file(h.home / ".kiro" / "skills" / "orgmcp" / "SKILL.md") == "text"


def test_an_existing_file_is_read(h: StoreHarness) -> None:
    h.put_file(h.base / "orgmcp" / "SKILL.md", "mine\n")
    assert h.store.read_existing(h.base) == "mine\n"


def test_a_target_that_is_not_a_file_is_an_org_error(h: StoreHarness) -> None:
    target = h.base / "orgmcp" / "SKILL.md"
    h.put_dir(target)
    with pytest.raises(OrgError) as raised:
        h.store.read_existing(h.base)
    assert str(raised.value) == f"{target} exists and is not a file; nothing was changed"


def test_a_directory_beside_the_target_is_no_hindrance(h: StoreHarness) -> None:
    h.put_dir(h.base / "orgmcp" / "other")
    assert h.store.read_existing(h.base) is None
    h.store.write(h.base, "x")
    assert h.store.read_existing(h.base) == "x"
