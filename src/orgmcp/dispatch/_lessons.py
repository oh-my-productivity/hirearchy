"""The lessons of a report on a service request. Skeleton: RED."""

from __future__ import annotations

from ..kernel import Message
from ._protocols import LessonsCheck

LESSONS_MAX_CHARS = 800  # longest `lessons` text a report on a service request may carry


class LessonsPolicy(LessonsCheck):
    """Requires lessons on a service request and keeps them short."""

    def check(self, task: Message, status: str, lessons: str | None) -> str:
        raise NotImplementedError
