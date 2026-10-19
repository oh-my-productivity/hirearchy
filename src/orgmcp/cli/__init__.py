"""orgmcp.cli: the command line of the human and of the runtime (see :mod:`orgmcp.cli.api`).

The module ``cli.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the old function name ``main`` is still
exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) by the private ``_legacy`` module until step E3 removes it.
"""

from . import api
from .api import *  # noqa: F403
from ._legacy import main

__all__ = [*api.__all__, "main"]
