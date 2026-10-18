"""Test support of ``templates``: the registry the contract suites iterate over, and a recording stand-in for consumers.

The real implementations are pure (same arguments, same bytes), so they need no in-memory fake: ``PURE`` says so (rule R8) and
``IMPLEMENTATIONS`` lists the real ones. ``RecordingNotices`` is for the unit tests of the packages that send notices.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from ._documents import StaticDocumentTemplates
from ._notices import StaticNotices
from .api import DocumentTemplates, Notices

PURE = True


def static_document_templates() -> DocumentTemplates:
    return StaticDocumentTemplates()


def static_notices() -> Notices:
    return StaticNotices()


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[], object]]] = {
    DocumentTemplates: [static_document_templates],
    Notices: [static_notices],
}


class RecordingNotices(Notices):
    """RED skeleton."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def budget(self, agent: str, unread: int) -> str:
        raise NotImplementedError

    def budget_returned(self, agent: str, amount: int, retired_by: str, reason: str) -> str:
        raise NotImplementedError

    def failures(self, agent: str, count: int, log: str, to_human: bool = True) -> str:
        raise NotImplementedError

    def nudge(self, task_id: str, title: str) -> str:
        raise NotImplementedError

    def stalled(self, agent: str, task_id: str, title: str, told: Sequence[str]) -> str:
        raise NotImplementedError

    def review_item(self, addr: str, flag: str, reason: str, act: bool = True, branch: str | None = None) -> str:
        raise NotImplementedError

    def review_manager(self, manager: str, items: Sequence[str]) -> str:
        raise NotImplementedError

    def review_root(self, summary: str, items: Sequence[str], skipped: Mapping[str, str]) -> str:
        raise NotImplementedError
