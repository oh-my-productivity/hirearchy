"""The old module-level names of ``orgmcp.upgrade``.

Exported by ``__init__`` until step E3 (``LEGACY_EXPORTS``). ``upgrade_rules`` still takes an ``Org``: a duck-typed one, because no
feature may import the facade."""

from __future__ import annotations

from ._host import UpgradedOrg
from ._report import Upgrade
from ._rules import MISSION_HEADING, RULES_HEADING, extract_mission

__all__ = ["MISSION_HEADING", "RULES_HEADING", "extract_mission", "upgrade_rules"]


def upgrade_rules(org: UpgradedOrg, dry_run: bool = False) -> Upgrade:
    """Rewrite the body of ORG.md to the current rules template (the mission is kept). ``dry_run`` writes nothing."""
    return org.runtime.rules_upgrader.upgrade_rules(dry_run)
