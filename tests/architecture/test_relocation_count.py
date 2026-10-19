"""No test is lost, duplicated or left unassigned by the relocation of ``tests/test_*.py`` (ARCHITECTURE.md 7.3, step E0).

``relocation.yaml`` (the manifest) names, for every destination file, the tests that move there and how many tests pytest collects
for each of them. Three checks, none of which runs the tests:

* (a) every test of every ``tests/test_*.py`` that is still there is assigned to exactly one destination (a new test fails here until
  somebody puts it in the manifest);
* (b) every manifest test that is no longer in its source (its group was applied, ``tools/relocate_tests.py apply --group X``) is
  collected at its destination, with the number of collected tests the manifest records: nothing lost, nothing duplicated;
* (c) the total number of collected tests never drops below the floor (the baseline, and the tests the manifest accounts for).
"""

from __future__ import annotations

import pytest

from . import collected_count, relocate_tool
from .paths import REPO

pytestmark = pytest.mark.architecture


@pytest.fixture(scope="module")
def tool():  # type: ignore[no-untyped-def]
    return relocate_tool.load()


@pytest.fixture(scope="module")
def manifest(tool):  # type: ignore[no-untyped-def]
    return tool.load_manifest(relocate_tool.MANIFEST)


def test_the_manifest_assigns_every_remaining_test_to_exactly_one_destination(tool, manifest) -> None:  # type: ignore[no-untyped-def]
    assigned = manifest.assignments()
    remaining = tool.source_inventory(REPO)
    unassigned = [f"{path}::{test}" for path, tests in remaining.items() for test in tests if (path, test) not in assigned]
    assert not unassigned, "not in tests/architecture/relocation.yaml (add them to the destination of their subject):\n  " + "\n  ".join(unassigned)


def test_the_manifest_names_no_test_twice_and_every_destination_in_the_group_of_its_package(tool, manifest) -> None:  # type: ignore[no-untyped-def]
    assert manifest.problems() == []


def test_a_group_that_was_applied_is_collected_at_its_destinations_as_the_manifest_says(tool, manifest) -> None:  # type: ignore[no-untyped-def]
    remaining = tool.source_inventory(REPO)
    moved = [t for t in manifest.tests() if t.test not in remaining.get(t.source, ())]
    if not moved:
        return  # nothing has moved yet: nothing to compare (and no collection to wait for)
    collected = collected_count.collect_ids()
    wrong = []
    for t in moved:
        actual = collected.get(t.destination, {}).get(t.test, 0)
        if actual != t.collected:
            wrong.append(f"{t.destination}::{t.test}: manifest {t.collected}, collected {actual} (from {t.source})")
    assert not wrong, "tests lost or duplicated by a move:\n  " + "\n  ".join(wrong)


def test_the_collected_total_never_drops_below_the_floor(manifest) -> None:  # type: ignore[no-untyped-def]
    total = sum(sum(tests.values()) for tests in collected_count.collect_ids().values())
    baseline = int(collected_count.BASELINE.read_text(encoding="utf-8").split()[0])
    accounted = sum(t.collected for t in manifest.tests())
    assert total >= max(baseline, accounted), f"{total} collected < floor {max(baseline, accounted)} (baseline {baseline}, manifest {accounted})"
