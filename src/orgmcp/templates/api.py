"""The public surface of ``templates``: the fixed prose the runtime writes into messages, ORG.md and charters.

Two Protocols, one per kind of text: the documents (``DocumentTemplates``) and the runtime notices (``Notices``). Both are
pure: the same arguments always give the same bytes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

__all__ = ["DocumentTemplates", "Notices"]


@runtime_checkable
class DocumentTemplates(Protocol):
    def org_rules(self, mission: str | None) -> str:
        """The ORG.md body: mission + the rules text."""
        ...

    def charter_body(self, role: str, charter: str) -> str:
        """The AGENT.md body (exactly one H1)."""
        ...

    def task_body(self, goal: str, acceptance: str, inputs: Sequence[str]) -> str:
        """Body of a task message."""
        ...

    def result_body(self, summary: str, artifacts: Sequence[str], lessons: str = "") -> str:
        """Body of a result message."""
        ...


@runtime_checkable
class Notices(Protocol):
    def budget(self, agent: str, unread: int) -> str:
        """Out-of-budget notice to the parent."""
        ...

    def budget_returned(self, agent: str, amount: int, retired_by: str, reason: str) -> str:
        """Refund note."""
        ...

    def failures(self, agent: str, count: int, log: str, to_human: bool = True) -> str:
        """'keeps failing' notice."""
        ...

    def nudge(self, task_id: str, title: str) -> str:
        """Stall reminder to the assignee."""
        ...

    def stalled(self, agent: str, task_id: str, title: str, told: Sequence[str]) -> str:
        """Stall escalation."""
        ...

    def review_item(self, addr: str, flag: str, reason: str, act: bool = True, branch: str | None = None) -> str:
        """One health item."""
        ...

    def review_manager(self, manager: str, items: Sequence[str]) -> str:
        """Health-review note to a manager."""
        ...

    def review_root(self, summary: str, items: Sequence[str], skipped: Mapping[str, str]) -> str:
        """Health-review note to root."""
        ...
