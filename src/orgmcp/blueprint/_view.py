"""Accessors over the normalized blueprint: the one place that knows its shape (package-private).

A blueprint is user text: any key may be missing or of the wrong type. Every accessor answers with an empty value for what it does not find,
and ``validate`` reports what is wrong. The schema of the keys (``NEEDS_KEYS``...) is here too, with the tool names the rules talk about."""
from __future__ import annotations
import re
from collections.abc import Iterable, Mapping
from typing import cast
from ..kernel import JsonObject
from .api import Issue
WEB_TOOLS = ('web_search', 'web_fetch')
WRITE_TOOLS = ('write', 'shell')
NEEDS_KEYS = {'scope', 'deliverable', 'quality_bar', 'sources', 'workspace', 'inputs', 'budget_runs', 'models', 'model_policy', 'review', 'approval', 'progress', 'kind', 'code'}
AGENT_KEYS = {'name', 'role', 'template', 'charter', 'model', 'tools', 'workspace', 'inputs', 'can_hire', 'max_children', 'children', 'scale', 'kind'}
SERVICE_KEYS = {'name', 'owner', 'description', 'inputs', 'acceptance', 'deliverable', 'budget', 'playbook', 'locked'}
TASK_KEYS = {'to', 'title', 'goal', 'acceptance', 'inputs', 'budget'}
REQUEST_KEYS = {'service', 'inputs', 'title', 'note', 'to'}

def s(value: object) -> str:
    raise NotImplementedError('red: C-blueprint-1')

def items(value: object) -> list[str]:
    """A list of words from a list or from text separated by commas and blanks."""
    raise NotImplementedError('red: C-blueprint-1')

def mapping_or_empty(value: object) -> JsonObject:
    raise NotImplementedError('red: C-blueprint-1')

def unknown(d: Mapping[str, object], known: set[str], where: str, issues: list[Issue]) -> None:
    raise NotImplementedError('red: C-blueprint-1')

def needs_of(bp: Mapping[str, object]) -> JsonObject:
    raise NotImplementedError('red: C-blueprint-1')

def task_of(bp: Mapping[str, object]) -> JsonObject:
    raise NotImplementedError('red: C-blueprint-1')

def deliverable_of(bp: Mapping[str, object]) -> JsonObject:
    raise NotImplementedError('red: C-blueprint-1')

def criteria_of(bp: Mapping[str, object]) -> list[str]:
    raise NotImplementedError('red: C-blueprint-1')

def services_of(bp: Mapping[str, object]) -> list[JsonObject]:
    """The service items of the blueprint that are mappings (``validate`` reports the others)."""
    raise NotImplementedError('red: C-blueprint-1')

def is_request(bp: Mapping[str, object]) -> bool:
    """The task is a first request for a service (``task.service``), not a plain task."""
    raise NotImplementedError('red: C-blueprint-1')

def is_plain(bp: Mapping[str, object]) -> bool:
    """Plain-task rules apply: no services, or a task that is not a request (deliverable, acceptance, goal required)."""
    raise NotImplementedError('red: C-blueprint-1')

def has_plain_task(bp: Mapping[str, object]) -> bool:
    raise NotImplementedError('red: C-blueprint-1')

def svc_deliverable(sv: Mapping[str, object]) -> JsonObject:
    raise NotImplementedError('red: C-blueprint-1')

def svc_criteria(sv: Mapping[str, object]) -> list[str]:
    raise NotImplementedError('red: C-blueprint-1')

def cap_of(needs: Mapping[str, object]) -> int | None:
    """The user's budget cap (runs) of one request, or None when there is none or it is not a whole number >= 1."""
    raise NotImplementedError('red: C-blueprint-1')
