"""Helpers shared by the tests of ``orgfiles`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import OrgError
from hirearchy.orgfiles.testing import OrgFilesHarness, StoreHarness


def make(request: pytest.FixtureRequest, tmp_path: Path) -> OrgFilesHarness:
    """The fixture body of the suites of the reader and the writer: the harness of one implementation."""
    return cast(Callable[[Path], OrgFilesHarness], request.param)(tmp_path)


def make_store(request: pytest.FixtureRequest, tmp_path: Path) -> StoreHarness:
    """The fixture body of the suite of the store: the harness of one implementation."""
    return cast(Callable[[Path], StoreHarness], request.param)(tmp_path)


def team(h: OrgFilesHarness) -> OrgFilesHarness:
    """``ceo`` (who has ``eng`` as its direct report) and ``ops``: two top-level agents."""
    h.add_agent("ceo", {"role": "CEO", "can_hire": True, "max_children": 2})
    h.add_agent("ceo/eng", {"role": "Engineer"})
    h.add_agent("ops", {"role": "Ops"})
    return h


def refusal(call: Callable[[], object]) -> str:
    """The text of the ``OrgError`` the call raises (the test fails when it raises nothing)."""
    with pytest.raises(OrgError) as caught:
        call()
    return str(caught.value)


def written(h: OrgFilesHarness, *parts: str) -> str | None:
    """The text of a file of the organization, None when there is none."""
    return h.read_back(h.root.joinpath(*parts))
