"""The same reviews as ``test_golden_notes.py``, through the reviewer of the runtime: the classes of the package say what ``review.py`` said."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from . import _scenario
from ._golden import expected
from .test_golden_notes import NAMES


def through_the_ports(org: Any, now: datetime, dry_run: bool = False) -> Any:
    return org.runtime.health_reviewer.review(now, dry_run)


@pytest.fixture
def seen(scenario: Any) -> dict[str, str]:
    return _scenario.observed(scenario, through_the_ports)


@pytest.mark.parametrize("name", NAMES)
def test_the_reviewer_of_the_runtime_says_what_review_py_said(seen: dict[str, str], name: str) -> None:
    assert seen[name] == expected(name)
