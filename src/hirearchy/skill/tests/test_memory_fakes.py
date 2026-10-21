"""The in-memory fakes beyond what the contract suites pin: their scripting helpers and their lexical path rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import OrgError
from hirearchy.skill import SkillSource, SkillStore
from hirearchy.skill.testing import MemorySkillSource, MemorySkillStore


def test_a_source_without_text_cannot_be_read_and_one_with_text_can() -> None:
    assert isinstance(MemorySkillSource(), SkillSource)
    with pytest.raises(OrgError):
        MemorySkillSource().read()
    assert MemorySkillSource("t").read() == "t"


def test_provide_and_remove_change_what_is_served() -> None:
    source = MemorySkillSource("a")
    source.remove()
    with pytest.raises(OrgError):
        source.read()
    source.provide("b")
    assert source.read() == "b"


def test_a_relative_destination_is_taken_from_the_working_directory() -> None:
    store = MemorySkillStore(cwd=Path("/work/here"))
    assert isinstance(store, SkillStore)
    assert store.target(Path("rel")) == Path("/work/here/rel/hirearchy/SKILL.md")


def test_the_home_is_the_one_it_was_given() -> None:
    assert MemorySkillStore(home=Path("/h")).target(None) == Path("/h/.kiro/skills/hirearchy/SKILL.md")
    assert MemorySkillStore(home=Path("/h")).target(Path("~")) == Path("/h/hirearchy/SKILL.md")


def test_reading_a_path_that_is_not_a_file_gives_none() -> None:
    store = MemorySkillStore()
    store.put_file(Path("/skills/hirearchy/SKILL.md"), "x")
    assert store.read_file(Path("/skills/hirearchy/SKILL.md")) == "x"
    assert store.read_file(Path("/skills/hirearchy")) is None and store.read_file(Path("/nothing")) is None


def test_two_stores_do_not_share_files() -> None:
    first, second = MemorySkillStore(), MemorySkillStore()
    first.write(Path("/s"), "x")
    assert second.read_existing(Path("/s")) is None
