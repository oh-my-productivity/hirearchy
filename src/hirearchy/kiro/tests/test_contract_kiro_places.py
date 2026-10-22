"""Contract of ``KiroPlaces``: where the kiro home and the working directories of one organization are (docs/design/kiro-runtime-v3.md 8.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kiro import KiroPlaces
from hirearchy.kiro.testing import IMPLEMENTATIONS, PlacesHarness

from ._support import make


@pytest.fixture(params=IMPLEMENTATIONS[KiroPlaces], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> PlacesHarness:
    made = make(request, tmp_path, PlacesHarness)
    assert isinstance(made.places, KiroPlaces) and isinstance(made.broken, KiroPlaces)
    return made


def test_the_home_is_under_the_first_root_and_the_scratch_under_the_second(h: PlacesHarness) -> None:
    homes, cwds = h.places.roots()
    assert h.places.home().is_absolute() and homes in h.places.home().parents
    assert h.places.scratch("ceo/eng").is_absolute() and cwds in h.places.scratch("ceo/eng").parents


def test_the_two_roots_are_absolute_and_distinct(h: PlacesHarness) -> None:
    homes, cwds = h.places.roots()
    assert homes.is_absolute() and cwds.is_absolute() and homes != cwds


def test_the_scratch_is_the_same_for_the_same_agent_and_differs_between_agents(h: PlacesHarness) -> None:
    assert h.places.scratch("ceo") == h.places.scratch("ceo") and h.places.scratch("ceo") != h.places.scratch("ceo/eng")


def test_a_valid_world_has_no_problem(h: PlacesHarness) -> None:
    assert h.places.problem() is None


def test_a_bad_world_has_a_problem_of_one_line(h: PlacesHarness) -> None:
    problem = h.broken.problem()
    assert isinstance(problem, str) and problem and "\n" not in problem


def test_computing_the_places_touches_no_file(h: PlacesHarness) -> None:
    before = sorted(h.base.rglob("*"))
    h.places.home(), h.places.scratch("ceo"), h.places.roots(), h.places.problem(), h.broken.problem()
    assert sorted(h.base.rglob("*")) == before
