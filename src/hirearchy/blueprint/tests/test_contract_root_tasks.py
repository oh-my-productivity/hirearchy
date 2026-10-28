"""Contract of ``RootTasks``: root's one-off tasks, by id (the fake here; the mail-backed one in ``app/tests/test_root_tasks.py``)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy.blueprint._protocols import RootTasks
from hirearchy.blueprint._shapes import RootTask
from hirearchy.blueprint.testing import IMPLEMENTATIONS, RootTasksHarness

from ._support import implementations, make

HEAD = RootTask("20261101T100000000001-a", datetime(2026, 11, 1, 10, tzinfo=timezone.utc), ("- Every row has a date.", "2. At most 3 pages."))


@pytest.fixture(params=implementations(IMPLEMENTATIONS[RootTasks]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> RootTasksHarness:
    made = make(request, tmp_path, RootTasksHarness)
    assert isinstance(made.tasks, RootTasks)
    return made


def test_a_task_that_is_not_there_is_none(h: RootTasksHarness) -> None:
    assert h.tasks.task("nothing") is None and h.tasks.task("") is None


def test_a_task_is_read_back_with_its_time_and_its_criteria_lines(h: RootTasksHarness) -> None:
    h.put(HEAD)
    assert h.tasks.task(HEAD.id) == HEAD
    assert h.tasks.task(HEAD.id + "x") is None
