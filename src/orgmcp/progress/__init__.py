"""orgmcp.progress: what the user reads back when they ask "status?" (see :mod:`orgmcp.progress.api`).

The module ``progress.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the old function names are still
exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) by the private ``_legacy`` module until step E3 removes them -
except ``progress(org, task_id=None, ...)``, which is part of the permanent compatibility surface (README). The private names the other legacy modules
import from here (``_human_items``, ``_state``, ...) are kept for them until their own steps.
"""

from . import api
from .api import *  # noqa: F403
from ._legacy import (
    FINAL,
    POLL,
    RECENT,
    SHORT,
    _artifacts as _artifacts,
    _can_run as _can_run,
    _human_items as _human_items,
    _last_activity as _last_activity,
    _needs_human as _needs_human,
    _runs as _runs,
    _section as _section,
    _state as _state,
    describe_progress,
    progress,
    work_in_flight,
)

__all__ = [*api.__all__, "FINAL", "POLL", "RECENT", "SHORT", "describe_progress", "progress", "work_in_flight"]
