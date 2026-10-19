"""orgmcp.scheduler: the heartbeat that runs the agents (see :mod:`orgmcp.scheduler.api`).

The module ``scheduler.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the old function and class
names are still exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) by the private ``_legacy`` module until step E3 removes them.

``EXIT_FILE``, ``FINISHED``, ``SchedulerState``, ``Waiting`` and ``run_id_of`` were only imported by the flat module, and callers still take them
from it: they are answered by name (``__getattr__``) from the packages that own them, which is not a new export.
"""

import importlib as _importlib
from datetime import datetime  # the golden fixtures replace it (``orgmcp.scheduler.datetime``): kept in the ledger of the legacy names

from . import api
from .api import *  # noqa: F403
from ._legacy import (
    KIRO_AGENTS_DIR,
    PROJECT_DIR,
    Run,
    Runner,
    Scheduler,
    describe_scheduler,
    ensure_kiro_profile,
    file_confinement,
    ignore_runtime_files,
    judge_orphan,
    kill_group,
    kiro_profile_name,
    kiro_runner,
    mcp_server_command,
    nothing_to_do,
    scheduler_command,
    scheduler_state,
    start_scheduler,
    stop_scheduler,
    waiting_on_user,
)
from ._legacy import _command_line as _command_line  # (private names the legacy callers and tests still use)
from ._legacy import _looks_like_scheduler_of as _looks_like_scheduler_of
from ._legacy import _ps as _ps
from ._legacy import _start_time as _start_time

__all__ = [
    *api.__all__,
    "KIRO_AGENTS_DIR",
    "PROJECT_DIR",
    "Run",
    "Runner",
    "Scheduler",
    "datetime",
    "describe_scheduler",
    "ensure_kiro_profile",
    "file_confinement",
    "ignore_runtime_files",
    "judge_orphan",
    "kill_group",
    "kiro_profile_name",
    "kiro_runner",
    "mcp_server_command",
    "nothing_to_do",
    "scheduler_command",
    "scheduler_state",
    "start_scheduler",
    "stop_scheduler",
    "waiting_on_user",
]

_OWNERS = {"EXIT_FILE": "daemon", "FINISHED": "daemon", "SchedulerState": "daemon", "Waiting": "attention", "run_id_of": "runs"}


def __getattr__(name: str) -> object:
    if name in _OWNERS:
        return getattr(_importlib.import_module(f"orgmcp.{_OWNERS[name]}"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
