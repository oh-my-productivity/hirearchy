"""The lessons of a report on a service request (moved from ``Org._check_lessons`` and ``core.LESSONS_MAX_CHARS``)."""

from __future__ import annotations

from ..kernel import Message, OrgError
from ._protocols import LessonsCheck

LESSONS_MAX_CHARS = 800  # longest `lessons` text a report on a service request may carry
AAR_FORM = (  # the after-action review the lessons of a service request take (design 11): five labelled parts, domain-agnostic
    "Expected: <the criterion id or step it concerns>. Happened: <what the work did>. Caught at: <where it should have been caught>. Cause: <the "
    "system cause: a step, a check, a hand-off, an input; not a person>. Prevent: <what would have prevented it>. When nothing went wrong: Near "
    "miss: <what almost went wrong, or none>."
)
LESSONS_MISSING = (
    "task {task} is a request for service `{service}`: pass `lessons` - an after-action review of the work, in these labelled parts: " + AAR_FORM
    + " Required for done, failed and blocked alike: a blocker is the most informative case, so say what went wrong and what would have "
    "prevented it"
)
LESSONS_TOO_LONG = (
    "lessons are {n} characters; the limit is {limit}. Keep the after-action review short: " + AAR_FORM + " Put detail in a file under your work/ directory."
)


def check_lessons(task: Message, status: str, lessons: str | None) -> str:
    """The lessons text for a report: required on a service request (done, failed or blocked), 1..800 characters."""
    text = (lessons or "").strip()
    if task.service and status in ("done", "failed", "blocked") and not text:
        raise OrgError(LESSONS_MISSING.format(task=task.id, service=task.service))
    if len(text) > LESSONS_MAX_CHARS:
        raise OrgError(LESSONS_TOO_LONG.format(n=len(text), limit=LESSONS_MAX_CHARS))
    return text


class LessonsPolicy(LessonsCheck):
    """Requires lessons on a service request and keeps them short."""

    def check(self, task: Message, status: str, lessons: str | None) -> str:
        """The lessons text for a report: required on a service request (done, failed or blocked), 1..800 characters."""
        return check_lessons(task, status, lessons)
