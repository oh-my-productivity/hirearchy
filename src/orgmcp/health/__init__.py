"""orgmcp.health: how well each agent and branch is doing, measured from the files (see :mod:`orgmcp.health.api`).

The module ``health.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the old function
names are still exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) by the private ``_legacy`` module until step E3
removes them. The private names the other legacy modules import from here (``_aware`` ... ``_number``) are kept for them until their
own steps.
"""

from . import api
from .api import *  # noqa: F403
from ._legacy import (
    FLAGS,
    HEALTH_DEFAULTS,
    AgentHealth,
    BranchHealth,
    OrgHealth,
    _aware as _aware,
    _duration as _duration,
    _msg_time as _msg_time,
    _number as _number,
    _parse_time as _parse_time,
    _stamp as _stamp,
    agent_health,
    config_number,
    org_health,
    render_text,
    thresholds,
)

__all__ = [*api.__all__, "agent_health", "config_number", "org_health", "render_text", "thresholds"]
