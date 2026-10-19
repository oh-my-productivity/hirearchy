"""orgmcp.review: turns the health of the organization into notes for the managers who can act on it (see :mod:`orgmcp.review.api`).

The module ``review.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the old function names
are still exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) by the private ``_legacy`` module until step E3 removes them.
"""

from . import api
from .api import *  # noqa: F403
from ._legacy import LEDGER, read_ledger, review, review_if_due, total_runs

__all__ = [*api.__all__, "LEDGER", "read_ledger", "review", "review_if_due", "total_runs"]
