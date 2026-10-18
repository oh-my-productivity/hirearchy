"""The old module-level functions of ``orgmcp.templates``, as thin adapters over the Protocol implementations.

Exported by ``__init__`` until step E3 (``LEGACY_EXPORTS``). ``kiro_profile`` is not a template of this package: it stays here,
unchanged, until step B-kiro moves it to ``kiro``.
"""

from __future__ import annotations

from ..kernel import JsonObject
from ._documents import DEFAULT_MISSION, ORG_RULES, StaticDocumentTemplates
from ._notices import REVIEW_ACTIONS, StaticNotices

__all__ = [
    "DEFAULT_MISSION", "ORG_RULES", "REVIEW_ACTIONS", "charter_body", "kiro_profile", "notice_budget", "notice_budget_returned",
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


def kiro_profile(
    name: str, description: str, tools: list[str], mcp_server: JsonObject, *,
    allowed_tools: list[str] | None = None, tools_settings: JsonObject | None = None,
) -> JsonObject:
    """A kiro-cli agent profile that loads only the orgmcp server (not the user's global mcp.json).

    ``allowed_tools`` = the tools kiro runs without asking (default: all of ``tools``). A tool that is NOT in it and has
    ``tools_settings`` with ``allowedPaths`` runs unprompted only on those paths; anything else needs an approval,
    which a ``--no-interactive`` run cannot give, so it is refused. A tool in ``allowed_tools`` ignores its
    ``allowedPaths`` entirely (only ``deniedPaths`` still apply), so confined tools must be left out of it.
    """
    data = {
        "name": name,
        "description": description,
        "prompt": (
            "You are a member of a file-based agent organization. The user message contains your "
            "rules, charter, memory, state and new messages for this run. Follow it exactly, act "
            "through the orgmcp tools, and stop when the messages are handled."
        ),
        "mcpServers": {"orgmcp": mcp_server},
        "tools": tools,
        "allowedTools": tools if allowed_tools is None else allowed_tools,
        "resources": [],
        "hooks": {},
        "includeMcpJson": False,
    }
    if tools_settings:
        data["toolsSettings"] = tools_settings
    return data
