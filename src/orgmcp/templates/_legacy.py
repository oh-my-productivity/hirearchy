"""The old module-level functions of ``orgmcp.templates``, as thin adapters over the Protocol implementations.

Exported by ``__init__`` until step E3 (``LEGACY_EXPORTS``).
"""

from __future__ import annotations

from ._documents import DEFAULT_MISSION, ORG_RULES, StaticDocumentTemplates
from ._notices import REVIEW_ACTIONS, StaticNotices

__all__ = [
    "DEFAULT_MISSION", "ORG_RULES", "REVIEW_ACTIONS", "charter_body", "notice_budget", "notice_budget_returned",
    "notice_failures", "notice_nudge", "notice_review_manager", "notice_review_root", "notice_stalled", "org_rules", "result_body",
    "review_item", "task_body",
]


def org_rules(mission: str | None) -> str:
    return StaticDocumentTemplates().org_rules(mission)


def charter_body(role: str, charter: str) -> str:
    return StaticDocumentTemplates().charter_body(role, charter)


def task_body(goal: str, acceptance: str, inputs: list[str]) -> str:
    return StaticDocumentTemplates().task_body(goal, acceptance, inputs)


def result_body(summary: str, artifacts: list[str], lessons: str = "") -> str:
    return StaticDocumentTemplates().result_body(summary, artifacts, lessons)


def notice_budget(agent: str, unread: int) -> str:
    return StaticNotices().budget(agent, unread)


def notice_budget_returned(agent: str, amount: int, retired_by: str, reason: str) -> str:
    return StaticNotices().budget_returned(agent, amount, retired_by, reason)


def notice_failures(agent: str, count: int, log: str, to_human: bool = True) -> str:
    return StaticNotices().failures(agent, count, log, to_human)


def notice_nudge(task_id: str, title: str) -> str:
    return StaticNotices().nudge(task_id, title)


def notice_stalled(agent: str, task_id: str, title: str, told: list[str]) -> str:
    return StaticNotices().stalled(agent, task_id, title, told)


def review_item(addr: str, flag: str, reason: str, act: bool = True, branch: str | None = None) -> str:
    return StaticNotices().review_item(addr, flag, reason, act, branch)


def notice_review_manager(manager: str, items: list[str]) -> str:
    return StaticNotices().review_manager(manager, items)


def notice_review_root(summary: str, items: list[str], skipped: dict[str, str]) -> str:
    return StaticNotices().review_root(summary, items, skipped)
