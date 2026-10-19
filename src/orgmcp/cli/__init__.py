"""orgmcp.cli: the command line of the human and of the runtime (see :mod:`orgmcp.cli.api`).

The module ``cli.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the old function names are still
exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) until step E3 removes them.
"""

from . import api
from .api import *  # noqa: F403
from ._legacy import (
    cmd_apply,
    cmd_define_service,
    cmd_dash,
    cmd_feedback,
    cmd_health,
    cmd_hire,
    cmd_inbox,
    cmd_init,
    cmd_install_skill,
    cmd_kiro_profile,
    cmd_mcp,
    cmd_plan,
    cmd_progress,
    cmd_request,
    cmd_resume,
    cmd_retire_service,
    cmd_review,
    cmd_run,
    cmd_send,
    cmd_services,
    cmd_status,
    cmd_task,
    cmd_upgrade_rules,
    main,
)

__all__ = [
    *api.__all__,
    "cmd_apply",
    "cmd_dash",
    "cmd_define_service",
    "cmd_feedback",
    "cmd_health",
    "cmd_hire",
    "cmd_inbox",
    "cmd_init",
    "cmd_install_skill",
    "cmd_kiro_profile",
    "cmd_mcp",
    "cmd_plan",
    "cmd_progress",
    "cmd_request",
    "cmd_resume",
    "cmd_retire_service",
    "cmd_review",
    "cmd_run",
    "cmd_send",
    "cmd_services",
    "cmd_status",
    "cmd_task",
    "cmd_upgrade_rules",
    "main",
]
