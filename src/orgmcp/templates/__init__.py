"""orgmcp.templates: the fixed prose the runtime writes (see :mod:`orgmcp.templates.api`).

The module ``templates.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the
old function and constant names are still exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) by the
private ``_legacy`` module until step E3 removes them.
"""

from . import api
from .api import *  # noqa: F403
from ._legacy import (
    DEFAULT_MISSION,
    ORG_RULES,
    REVIEW_ACTIONS,
    charter_body,
    notice_budget,
    notice_budget_returned,
    notice_failures,
    notice_nudge,
    notice_review_manager,
    notice_review_root,
    notice_stalled,
    org_rules,
    result_body,
    review_item,
    task_body,
)

__all__ = [
    *api.__all__,
    "DEFAULT_MISSION",
    "ORG_RULES",
    "REVIEW_ACTIONS",
    "charter_body",
    "notice_budget",
    "notice_budget_returned",
    "notice_failures",
    "notice_nudge",
    "notice_review_manager",
    "notice_review_root",
    "notice_stalled",
    "org_rules",
    "result_body",
    "review_item",
    "task_body",
]
