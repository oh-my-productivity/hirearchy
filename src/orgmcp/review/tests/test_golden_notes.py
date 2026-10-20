"""The notes, the renderings and the ledger of the reviews of ``_scenario``, byte for byte as ``review.py`` produced them before the package existed.

They are asked through ``testkit.review_world``, which gives the reviewer of the runtime the call shape the tests have always used."""

from __future__ import annotations

from typing import Any

import pytest
from testkit.review_world import review

from . import _scenario
from ._golden import expected

NAMES = ["dry_run.txt", "first.txt", "second.txt", "notes.txt", "ledger.json", "first_summary.json"]


@pytest.fixture
def seen(scenario: Any) -> dict[str, str]:
    return _scenario.observed(scenario, review)


@pytest.mark.parametrize("name", NAMES)
def test_the_reviews_say_what_review_py_said(seen: dict[str, str], name: str) -> None:
    assert seen[name] == expected(name)


def test_every_expected_file_is_checked() -> None:
    from . import _golden

    assert sorted(p.name for p in _golden.EXPECTED.iterdir()) == sorted(NAMES)
