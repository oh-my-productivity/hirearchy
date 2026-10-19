"""orgmcp.blueprint: a whole organization for one goal as a reviewable document (see :mod:`orgmcp.blueprint.api`).

The module ``blueprint.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the old function and
constant names are still exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) by the private ``_legacy`` module until step E3
removes them. The first part of the old module (the role library, loading, the agents, the rules of ``validate``, the access report, the budget
estimate) is classes behind the interfaces of ``api`` (step C-blueprint-1); ``_legacy`` keeps what step C-blueprint-2 moves next: the charters, the
plan and its identity, ``apply``, and the budget split.
"""

from . import _access as _access_module  # noqa: F401 - loaded first: the legacy FUNCTION ``_access`` below must not be replaced by its module's name
from . import api
from .api import *  # noqa: F403
from ._legacy import (
    AGENT_KEYS,
    CLIP,
    GOAL_CLIP,
    HIDDEN_WARNINGS,
    KINDS,
    NEEDS_KEYS,
    PLAN_DRAFT_HEADING,
    PLAN_END,
    PLAN_HEADING,
    PLAN_ID_LENGTH,
    PLAN_SHOW,
    REQUEST_KEYS,
    REWORK_RUNS,
    ROLES_DIR,
    SERVICE_KEYS,
    SHOWN_CRITERIA,
    SHOWN_SERVICE_CRITERIA,
    SHOWN_WARNINGS,
    SLACK,
    Summary,
    TASK_KEYS,
    TIGHT,
    TOOL_WORDS,
    WEB_TOOLS,
    WRITE_TOOLS,
    access_facts,
    apply,
    budget_split,
    declared_inputs,
    default_playbook,
    edits_others_files,
    estimate,
    get_role,
    load,
    load_text,
    org_files_readable,
    plan_for_user,
    plan_id,
    planned_total,
    propose,
    propose_text,
    render_plan,
    review_roots,
    role_names,
    service_budget,
    validate,
)
from ._legacy import _access as _access
from ._legacy import _agent_access as _agent_access
from ._legacy import _resolve as _resolve
from ._rules import blob as _blob  # (the private names the tests still reach for, from where they live now)
from ._rules import is_code as _is_code
from ._text import clip as _clip
from ._view import is_plain as _plain
from ._view import is_request as _is_request

__all__ = [
    *api.__all__,
    "AGENT_KEYS",
    "CLIP",
    "GOAL_CLIP",
    "HIDDEN_WARNINGS",
    "KINDS",
    "NEEDS_KEYS",
    "PLAN_DRAFT_HEADING",
    "PLAN_END",
    "PLAN_HEADING",
    "PLAN_ID_LENGTH",
    "PLAN_SHOW",
    "REQUEST_KEYS",
    "REWORK_RUNS",
    "ROLES_DIR",
    "SERVICE_KEYS",
    "SHOWN_CRITERIA",
    "SHOWN_SERVICE_CRITERIA",
    "SHOWN_WARNINGS",
    "SLACK",
    "Summary",
    "TASK_KEYS",
    "TIGHT",
    "TOOL_WORDS",
    "WEB_TOOLS",
    "WRITE_TOOLS",
    "access_facts",
    "apply",
    "budget_split",
    "declared_inputs",
    "default_playbook",
    "edits_others_files",
    "estimate",
    "get_role",
    "load",
    "load_text",
    "org_files_readable",
    "plan_for_user",
    "plan_id",
    "planned_total",
    "propose",
    "propose_text",
    "render_plan",
    "review_roots",
    "role_names",
    "service_budget",
    "validate",
]
