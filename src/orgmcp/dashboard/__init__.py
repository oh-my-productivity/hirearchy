"""orgmcp.dashboard: the terminal dashboard of ``orgmcp dash`` (see :mod:`orgmcp.dashboard.api`).

The module ``dashboard.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the old names that are still
used are exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) until step E3 removes them: ``DashApp`` and ``run_dashboard`` by the
private ``_legacy`` module (the old way in: a root path), ``TextPane``, ``NavTable`` and ``TextScreen`` (widgets the tests look at) by ``_widgets``.
"""

from . import api
from .api import *  # noqa: F403
from ._legacy import DashApp, run_dashboard
from ._widgets import NavTable, TextPane, TextScreen

__all__ = [*api.__all__, "DashApp", "NavTable", "TextPane", "TextScreen", "run_dashboard"]
