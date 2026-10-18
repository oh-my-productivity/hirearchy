"""The notices the runtime sends: budget, failures, stalls, health reviews."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .api import Notices


class StaticNotices(Notices):
    """Renders the notices from fixed text (RED skeleton)."""

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
