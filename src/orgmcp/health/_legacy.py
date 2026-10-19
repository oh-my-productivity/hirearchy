"""The old module-level names of ``orgmcp.health``, as thin adapters over the classes of the package.

Exported by ``__init__`` until step E3 (``LEGACY_EXPORTS``). Each function takes the ``Org`` it is given (a feature may not import the facade,
so it is duck-typed) and works over the ports that ``Org`` has *now* (``_assembly``).

The private time helpers and numeric readers below are what other legacy modules still import from here, until their own steps:

* ``_aware _parse_time _stamp _msg_time _duration``: ``dashboard_data`` (``_aware _stamp``), ``observe`` (``_aware _stamp``), ``progress``
  (``_aware _duration _stamp``), ``review`` (``_aware _parse_time``), ``services`` (``_msg_time _parse_time``);
* ``config_number``: ``dashboard_data``, ``observe``, ``review``, ``scheduler``; ``_number``: the settings tests.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ..kernel import ROOT, aware, fmt_duration, msg_time, parse_time, stamp_of
from ..settings import config_number as config_number  # re-export (legacy name health.config_number)
from ..settings import finite_number
from ._assembly import analyzer_of, thresholds_of
from ._render import TextHealthRenderer
from .api import FLAGS, HEALTH_DEFAULTS, AgentHealth, BranchHealth, OrgHealth

Org = Any  # the facade (a feature may not import it): the functions below take whatever has its methods

__all__ = [
    "FLAGS", "HEALTH_DEFAULTS", "AgentHealth", "BranchHealth", "OrgHealth", "agent_health", "config_number", "org_health", "render_text",
    "thresholds",
]


def thresholds(org: Org) -> dict[str, float]:
    """HEALTH_DEFAULTS merged with the ``health:`` mapping of ORG.md.

    A value that is not a finite number falls back to its default (a typo in ORG.md must not break health).
    """
    return thresholds_of(org).thresholds()


def agent_health(org: Org, addr: str, now: datetime | None = None, limits: Mapping[str, float] | None = None) -> AgentHealth:
    """Metrics and flags for one agent. ``now`` defaults to the current time; ``limits`` to ``thresholds(org)``."""
    return analyzer_of(org).agent_health(addr, now, limits)


def org_health(org: Org, root: str = ROOT, now: datetime | None = None) -> OrgHealth:
    """Health of ``root`` and everything below it (``root`` = the whole organization, human excluded)."""
    return analyzer_of(org).org_health(root, now)


def render_text(health: OrgHealth) -> str:
    """Human report: a summary line, then one line per agent (indented by depth) with flags and reasons."""
    return TextHealthRenderer().render_text(health)


# ---------------------------------------------------------------- helpers other legacy modules still import


_number = finite_number
_aware = aware
_parse_time = parse_time
_stamp = stamp_of
_msg_time = msg_time
_duration = fmt_duration
