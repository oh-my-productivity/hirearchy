"""``AgentSlots``: is something at the place of an agent. The real one looks at the directory, the fake at its tree; they agree."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from hirearchy.agents.testing import MemoryAgents
from hirearchy.hierarchy._ports import AgentSlots
from hirearchy.hierarchy._slots import FsAgentSlots
from hirearchy.hierarchy.testing import MemoryAgentSlots
from hirearchy.kernel import OrgPaths


class Place:
    """One implementation and the means to make things happen at the places it looks at."""

    def __init__(self, slots: AgentSlots, directory: Callable[[str], None], file: Callable[[str], None]) -> None:
        self.slots = slots
        self.directory = directory
        self.file = file


def on_disk(tmp_path: Path) -> Place:
    def directory(path: str) -> None:
        (tmp_path / path).mkdir(parents=True, exist_ok=True)

    def file(path: str) -> None:
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text("x", encoding="utf-8")

    return Place(FsAgentSlots(OrgPaths(tmp_path)), directory, file)


def in_memory(tmp_path: Path) -> Place:
    files = MemoryAgents()
    return Place(MemoryAgentSlots(files), files.put_dir, lambda path: files.put(path, "x"))


@pytest.fixture(params=[on_disk, in_memory], ids=lambda factory: factory.__name__)
def place(request: pytest.FixtureRequest, tmp_path: Path) -> Place:
    made: Place = request.param(tmp_path)
    assert isinstance(made.slots, AgentSlots)
    return made


def test_a_place_with_nothing_is_free(place: Place) -> None:
    assert not place.slots.occupied("ceo") and not place.slots.occupied("ceo/eng")


def test_a_directory_occupies_its_place_whether_or_not_it_is_an_agent(place: Place) -> None:
    place.directory("ceo/eng")  # no AGENT.md: not an agent, but hiring there would collide
    assert place.slots.occupied("ceo/eng") and place.slots.occupied("ceo")


def test_a_file_occupies_its_place(place: Place) -> None:
    place.file("notes")
    assert place.slots.occupied("notes")


def test_the_place_below_a_free_place_is_free(place: Place) -> None:
    place.directory("ceo")
    assert not place.slots.occupied("ceo/eng")


def test_the_address_is_normalized(place: Place) -> None:
    place.directory("ceo")
    assert place.slots.occupied("ceo/") and place.slots.occupied(" ceo ")
