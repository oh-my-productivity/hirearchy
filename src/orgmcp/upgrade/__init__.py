"""orgmcp.upgrade: bringing an organization's ORG.md rules up to the current template (see :mod:`orgmcp.upgrade.api`).

The module ``upgrade.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the old names
are still exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) by the private ``_legacy`` module until step E3
removes them.
"""

from . import api
from .api import *  # noqa: F403
from ._legacy import MISSION_HEADING, RULES_HEADING, extract_mission, upgrade_rules

__all__ = [*api.__all__, "MISSION_HEADING", "RULES_HEADING", "extract_mission", "upgrade_rules"]
