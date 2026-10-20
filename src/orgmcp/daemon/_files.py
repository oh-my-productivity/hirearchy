"""Where the scheduler's files are (``.runtime/scheduler.pid``, ``.exit`` and ``.log``)."""

from __future__ import annotations

from pathlib import Path

from ..kernel import OrgLayout


def pidfile_of(layout: OrgLayout) -> Path:
    """``.runtime/scheduler.pid``: the pid of the running scheduler, written by the scheduler process itself."""
    return layout.runtime_dir() / "scheduler.pid"


def exit_file_of(layout: OrgLayout) -> Path:
    """``.runtime/scheduler.exit``: why the last scheduler exited by itself."""
    return layout.runtime_dir() / "scheduler.exit"


def log_of(layout: OrgLayout) -> Path:
    """``.runtime/scheduler.log``: the output of the schedulers that were started detached."""
    return layout.runtime_dir() / "scheduler.log"
