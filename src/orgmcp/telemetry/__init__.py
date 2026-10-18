"""orgmcp.telemetry: the event log, emission side (see :mod:`orgmcp.telemetry.api`).

The module ``telemetry.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the old
function and constant names are still exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) by the private
``_legacy`` module until step E3 removes them.
"""

from . import api
from .api import *  # noqa: F403
from ._legacy import (
    DAY_RE,
    ENVELOPE,
    ERROR_MAX,
    EVENTS_REL,
    LINE_MAX,
    PROCS,
    RETRY_AFTER,
    SCHEMA_VERSION,
    TITLE_MAX,
    clip,
    datetime,
    dropped,
    emit,
    ensure_ignored,
    note_trace,
    process,
    prune,
    reset,
    set_process,
    single,
    summarize_args,
    traces_seen,
)

__all__ = [
    *api.__all__,
    "DAY_RE",
    "ENVELOPE",
    "ERROR_MAX",
    "EVENTS_REL",
    "LINE_MAX",
    "PROCS",
    "RETRY_AFTER",
    "SCHEMA_VERSION",
    "TITLE_MAX",
    "clip",
    "datetime",
    "dropped",
    "emit",
    "ensure_ignored",
    "note_trace",
    "process",
    "prune",
    "reset",
    "set_process",
    "single",
    "summarize_args",
    "traces_seen",
]
