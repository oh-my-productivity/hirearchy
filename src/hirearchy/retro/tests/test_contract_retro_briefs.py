"""Contract of ``RetroBriefs``: a call returns the brief; the real class over fixed facts and the fake answer the same shape."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from hirearchy.retro import Brief, RetroBriefs
from hirearchy.retro.testing import IMPLEMENTATIONS


@pytest.fixture(params=IMPLEMENTATIONS[RetroBriefs], ids=lambda factory: factory.__name__)
def briefs(request: pytest.FixtureRequest, tmp_path: Path) -> RetroBriefs:
    made = request.param(tmp_path)
    assert isinstance(made, RetroBriefs)
    return made


def test_a_call_returns_a_brief_with_an_id_and_a_time(briefs: RetroBriefs) -> None:
    brief = briefs.brief()
    assert isinstance(brief, Brief) and brief.id and brief.at.tzinfo is not None and isinstance(brief.sections, tuple) and len(brief.items) <= 3


def test_a_look_back_returns_a_brief_too(briefs: RetroBriefs) -> None:
    brief = briefs.brief()
    assert isinstance(briefs.brief(since=brief.at - timedelta(days=30)), Brief)
