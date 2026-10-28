"""Accessors over the normalized blueprint: the one place that knows its shape (package-private).

A blueprint is user text: any key may be missing or of the wrong type. Every accessor answers with an empty value for what it does not find,
and ``validate`` reports what is wrong. The schema of the keys (``NEEDS_KEYS``...) is here too, with the tool names the rules talk about."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import cast

from ..kernel import JsonObject
from .api import Issue

WEB_TOOLS = ("web_search", "web_fetch")
WRITE_TOOLS = ("write", "shell")

NEEDS_KEYS = {"scope", "deliverable", "quality_bar", "sources", "workspace", "inputs", "budget_runs", "models",
              "model_policy", "review", "approval", "progress", "kind", "code", "elicitation"}
AGENT_KEYS = {"name", "role", "template", "charter", "model", "tools", "workspace", "inputs", "can_hire", "max_children",
              "children", "scale", "kind"}
SERVICE_KEYS = {"name", "owner", "description", "inputs", "acceptance", "deliverable", "budget", "playbook", "locked"}
TASK_KEYS = {"to", "title", "goal", "acceptance", "inputs", "budget"}
REQUEST_KEYS = {"service", "inputs", "title", "note", "to"}  # a task that is a first request for a service


def s(value: object) -> str:
    return "" if value is None else str(value).strip()


def items(value: object) -> list[str]:
    """A list of words from a list or from text separated by commas and blanks."""
    if value is None:
        return []
    if isinstance(value, str):
        return [t for t in re.split(r"[,\s]+", value) if t]
    return [str(v).strip() for v in cast("Iterable[object]", value) if str(v).strip()]


def mapping_or_empty(value: object) -> JsonObject:
    return value if isinstance(value, dict) else {}


def unknown(d: Mapping[str, object], known: set[str], where: str, issues: list[Issue]) -> None:
    for k in d:
        if k not in known:
            issues.append(Issue("warning", where, f"unknown key '{k}' is ignored; check the spelling (known: {', '.join(sorted(known))})", "unknown-key"))


def needs_of(bp: Mapping[str, object]) -> JsonObject:
    return mapping_or_empty(bp.get("needs"))


def task_of(bp: Mapping[str, object]) -> JsonObject:
    return mapping_or_empty(bp.get("task"))


def deliverable_of(bp: Mapping[str, object]) -> JsonObject:
    d = needs_of(bp).get("deliverable")
    if isinstance(d, str):
        return {"description": d}
    return mapping_or_empty(d)


def criterion_text(c: object) -> str:
    """The words of one acceptance criterion: a string is itself, a mapping (``{text, from | default | from_tasks, asked}``) is its ``text`` alone.
    The source is never part of a criterion's words (design 10.1 step 5)."""
    return s(c.get("text")) if isinstance(c, dict) else s(c)


def criteria_of(bp: Mapping[str, object]) -> list[str]:
    t = bp.get("task")
    acc = t.get("acceptance") if isinstance(t, dict) else None
    return [criterion_text(c) for c in acc] if isinstance(acc, list) else []


def services_of(bp: Mapping[str, object]) -> list[JsonObject]:
    """The service items of the blueprint that are mappings (``validate`` reports the others)."""
    raw = bp.get("services")
    return [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []


def is_request(bp: Mapping[str, object]) -> bool:
    """The task is a first request for a service (``task.service``), not a plain task."""
    t = bp.get("task")
    return isinstance(t, dict) and "service" in t


def is_plain(bp: Mapping[str, object]) -> bool:
    """Plain-task rules apply: no services, or a task that is not a request (deliverable, acceptance, goal required)."""
    t = bp.get("task")
    return not services_of(bp) or (isinstance(t, dict) and "service" not in t)


def has_plain_task(bp: Mapping[str, object]) -> bool:
    t = bp.get("task")
    return isinstance(t, dict) and "service" not in t


def svc_deliverable(sv: Mapping[str, object]) -> JsonObject:
    d = sv.get("deliverable")
    if isinstance(d, str):
        return {"description": d}
    return mapping_or_empty(d)


def svc_criteria(sv: Mapping[str, object]) -> list[str]:
    acc = sv.get("acceptance")
    return [text for c in acc if (text := criterion_text(c))] if isinstance(acc, list) else []


def cap_of(needs: Mapping[str, object]) -> int | None:
    """The user's budget cap (runs) of one request, or None when there is none or it is not a whole number >= 1."""
    c = needs.get("budget_runs")
    return c if isinstance(c, int) and not isinstance(c, bool) and c >= 1 else None
