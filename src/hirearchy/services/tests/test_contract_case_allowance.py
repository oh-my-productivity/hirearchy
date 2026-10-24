"""Contract of ``CaseAllowance``: for a rework of a request, what is left of the runs the user approved for its case (D-E5-1, design 4.5).

Every implementation answers for the service ``weekly-brief`` of ``ceo``. What the callers rely on: ``None`` for a task that is in no case; otherwise an
``int`` (0 or below when nothing is left), the same every time. The real one (``reflection.CaseAllowanceOf``) runs this suite too, over a world with
cases: ``reflection/tests/test_case_allowance.py``."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.services import CaseAllowance
from hirearchy.services.testing import ALLOWANCE_TASK, IMPLEMENTATIONS

from ._support import implementations

OWNER, SERVICE = "ceo", "weekly-brief"


@pytest.fixture(params=implementations(IMPLEMENTATIONS[CaseAllowance]))
def allowance(request: pytest.FixtureRequest, tmp_path: Path) -> CaseAllowance:
    made = request.param(tmp_path)
    assert isinstance(made, CaseAllowance)
    return made


def test_a_task_that_is_in_no_case_has_no_allowance(allowance: CaseAllowance) -> None:
    assert allowance.left(OWNER, SERVICE, "20200101T000000000001-root-0000") is None


def test_the_answer_is_none_or_a_whole_number_of_runs(allowance: CaseAllowance) -> None:
    got = allowance.left(OWNER, SERVICE, ALLOWANCE_TASK)
    assert got is None or (isinstance(got, int) and not isinstance(got, bool))


def test_the_answer_is_the_same_every_time(allowance: CaseAllowance) -> None:
    assert allowance.left(OWNER, SERVICE, ALLOWANCE_TASK) == allowance.left(OWNER, SERVICE, ALLOWANCE_TASK)
