"""Contract of ``RetroDue``: a line for a reply or a listing, or an empty one; never an exception. The real class over fixed facts and the fake answer the same shape."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.retro import RetroDue
from hirearchy.retro.testing import IMPLEMENTATIONS


@pytest.fixture(params=IMPLEMENTATIONS[RetroDue], ids=lambda factory: factory.__name__)
def due(request: pytest.FixtureRequest, tmp_path: Path) -> RetroDue:
    made = request.param(tmp_path)
    assert isinstance(made, RetroDue)
    return made


def test_a_reply_and_a_listing_are_one_line_or_empty(due: RetroDue) -> None:
    for line in (due.due(), due.due(listing=True)):
        assert isinstance(line, str) and "\n" not in line and (line == "" or line.startswith("Retro due: "))
