"""orgmcp.dashboard: the terminal dashboard of ``orgmcp dash`` (see :mod:`orgmcp.dashboard.api`).

The module ``dashboard.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the old names that are still
used are exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) by the private ``_legacy`` module until step E3 removes them.
"""

from . import api
from .api import *  # noqa: F403
from ._legacy import DashApp, NavTable, TextPane, TextScreen, run_dashboard

__all__ = [*api.__all__, "DashApp", "NavTable", "TextPane", "TextScreen", "run_dashboard"]
