"""The number of collected tests never drops (ARCHITECTURE.md section 7: moves keep every test, nothing is deleted or skipped away).

Two floors, neither of which is a shared line that two parallel steps both edit (9.2):

* ``baseline_test_count.txt`` is the count of the commit the scaffold was built on. It is fixed: no step edits it (tests only move
  and grow), so it needs no merge.
* every colocated ``src/hirearchy/<pkg>/tests/`` directory records its own floor in ``count.txt`` beside its tests (the step that owns the package
  creates it and raises it when it adds tests; ``uv run python -m tests.architecture.collected_count --write`` writes it). Lowering a floor
  is a review item, as lowering the baseline was.
"""

from __future__ import annotations

import pytest

from . import collected_count
from .paths import REPO

pytestmark = pytest.mark.architecture

FLOORS = collected_count.floor_files()


@pytest.fixture(scope="module")
def collected() -> dict[str, int]:
    return collected_count.collect()


def test_the_collected_count_is_at_least_the_baseline(collected: dict[str, int]) -> None:
    baseline = int(collected_count.BASELINE.read_text(encoding="utf-8").split()[0])
    total = sum(collected.values())
    assert total >= baseline, f"{total} collected < baseline {baseline}: a test was deleted or lost"


@pytest.mark.parametrize("floor_file", FLOORS, ids=lambda p: str(p.parent.relative_to(REPO)))
def test_a_directory_keeps_the_tests_it_recorded(floor_file, collected: dict[str, int]) -> None:  # type: ignore[no-untyped-def]
    directory = floor_file.parent.relative_to(REPO).as_posix()
    floor = int(floor_file.read_text(encoding="utf-8").split()[0])
    count = sum(n for path, n in collected.items() if path.startswith(directory + "/"))
    assert count >= floor, f"{directory}: {count} collected < recorded {floor}: a test was deleted or lost"


def test_every_colocated_tests_directory_records_its_floor() -> None:
    assert collected_count.directories_without_floor() == []


def test_the_floor_files_are_found_beside_the_tests() -> None:
    assert FLOORS and all(f.name == "count.txt" and (f.parent / "__init__.py").is_file() for f in FLOORS)
