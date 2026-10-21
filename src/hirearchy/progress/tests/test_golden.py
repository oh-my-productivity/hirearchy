"""The texts of ``progress`` on ``_scenario``'s organization, byte for byte as the module ``progress.py`` made them before the package existed.

They are asked of the permanent function ``progress(org, task_id)`` and of the reporter of the runtime."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from hirearchy.progress import progress

from . import _scenario

EXPECTED = Path(__file__).with_name("expected")
Ask = Callable[[Any, str | None, datetime], str]


def expected(name: str) -> str:
    return (EXPECTED / name).read_text(encoding="utf-8")


def by_function(org: Any, task_id: str | None, now: datetime) -> str:
    return progress(org, task_id, now=now)


def by_reporter(org: Any, task_id: str | None, now: datetime) -> str:
    return str(org.runtime.progress_reporter.progress(task_id, now))


@pytest.fixture(params=[by_function, by_reporter], ids=["function", "reporter"])
def ask(request: pytest.FixtureRequest) -> Ask:
    return request.param  # type: ignore[no-any-return]


def test_every_task_and_what_needs_the_user(scenario: Any, ask: Ask) -> None:
    assert ask(scenario, None, _scenario.NOW) + "\n" == expected("all.txt")


def test_finished_tasks_are_only_listed_for_a_day(scenario: Any, ask: Ask) -> None:
    assert ask(scenario, None, _scenario.NOW.replace(day=9)) + "\n" == expected("all_later.txt")


def test_each_task_alone_in_whatever_state(scenario: Any, ask: Ask) -> None:
    tasks = [m for m in scenario.sent(_scenario.ROOT) if m.type == "task"]
    assert len(tasks) == 9
    for i, task in enumerate(tasks):
        name = f"task_{i}_{task.title.lower().split(':')[0].replace(' ', '_')}.txt"
        assert ask(scenario, task.id, _scenario.NOW) + "\n" == expected(name), name


def test_the_waits(scenario: Any) -> None:
    assert _scenario.wait_cases(scenario, progress) == expected("waits.txt")
