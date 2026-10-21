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
    """Records every notice asked for (``calls``: method name and all arguments, defaults filled in) and returns a short text
    that names the method and the arguments, so a consumer's test can assert on what it sent without the real wording."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def _record(self, method: str, *args: object) -> str:
        shown = tuple(tuple(a) if isinstance(a, (list, tuple)) else a for a in args)
        self.calls.append((method, shown))
        return f"{method}: " + " | ".join(str(a) for a in args)

    def budget(self, agent: str, unread: int) -> str:
        return self._record("budget", agent, unread)

    def budget_returned(self, agent: str, amount: int, retired_by: str, reason: str) -> str:
        return self._record("budget_returned", agent, amount, retired_by, reason)

    def failures(self, agent: str, count: int, log: str, to_human: bool = True) -> str:
        return self._record("failures", agent, count, log, to_human)

    def nudge(self, task_id: str, title: str) -> str:
        return self._record("nudge", task_id, title)

    def stalled(self, agent: str, task_id: str, title: str, told: Sequence[str]) -> str:
        return self._record("stalled", agent, task_id, title, told)

    def review_item(self, addr: str, flag: str, reason: str, act: bool = True, branch: str | None = None) -> str:
        return self._record("review_item", addr, flag, reason, act, branch)

    def review_manager(self, manager: str, items: Sequence[str]) -> str:
        return self._record("review_manager", manager, items)

    def review_root(self, summary: str, items: Sequence[str], skipped: Mapping[str, str]) -> str:
        return self._record("review_root", summary, items, skipped)
