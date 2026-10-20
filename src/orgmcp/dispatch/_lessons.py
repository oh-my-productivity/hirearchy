"""The lessons of a report on a service request (moved from ``Org._check_lessons`` and ``core.LESSONS_MAX_CHARS``)."""

from __future__ import annotations

from ..kernel import Message, OrgError
from ._protocols import LessonsCheck

LESSONS_MAX_CHARS = 800  # longest `lessons` text a report on a service request may carry


def check_lessons(task: Message, status: str, lessons: str | None) -> str:
    """The lessons text for a report: required on a service request (done, failed or blocked), 1..800 characters."""
    text = (lessons or "").strip()
    if task.service and status in ("done", "failed", "blocked") and not text:
        raise OrgError(
            f"task {task.id} is a request for service `{task.service}`: pass `lessons` - 1-3 lines for the next "
            "request: what worked, what to change in the playbook, and the evidence (runs, rework, review "
            "findings). Required for done, failed and blocked alike: a blocker is the most informative case, so "
            "say what went wrong and what would have prevented it"
        )
    if len(text) > LESSONS_MAX_CHARS:
        raise OrgError(
            f"lessons are {len(text)} characters; the limit is {LESSONS_MAX_CHARS}. Keep 1-3 lines: what worked, "
            "what to change in the playbook, and the evidence; put detail in a file under your work/ directory."
        )
    return text


class LessonsPolicy(LessonsCheck):
    """Requires lessons on a service request and keeps them short."""

    def check(self, task: Message, status: str, lessons: str | None) -> str:
        """The lessons text for a report: required on a service request (done, failed or blocked), 1..800 characters."""
        return check_lessons(task, status, lessons)
