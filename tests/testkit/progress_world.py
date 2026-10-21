"""``describe_progress(org, task_id, wait_seconds)`` and ``work_in_flight(org, task_id)`` as the tests call them: over the ``ProgressReporter`` of the runtime of the organization.

(``progress(org, ...)`` is the permanent entry point of ``hirearchy.progress`` and is imported from there.)
"""

from __future__ import annotations

from typing import Any


def describe_progress(org: Any, task_id: str | None = None, wait_seconds: int = 0) -> str:
    return org.runtime.progress_reporter.describe_progress(task_id, wait_seconds)  # type: ignore[no-any-return]


def work_in_flight(org: Any, task_id: str | None = None) -> bool:
    return org.runtime.progress_reporter.work_in_flight(task_id)  # type: ignore[no-any-return]
