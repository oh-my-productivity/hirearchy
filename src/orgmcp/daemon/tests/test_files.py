"""Where the scheduler's files are: ``.runtime/scheduler.pid``, ``.exit`` and ``.log`` below the organization root."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.daemon import EXIT_FILE
from orgmcp.daemon._files import exit_file_of, log_of, pidfile_of
from orgmcp.kernel import OrgPaths

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-daemon")


def test_the_three_files_are_in_the_runtime_directory(tmp_path: Path) -> None:
    layout = OrgPaths(tmp_path)
    assert pidfile_of(layout) == tmp_path / ".runtime" / "scheduler.pid"
    assert exit_file_of(layout) == tmp_path / ".runtime" / "scheduler.exit"
    assert log_of(layout) == tmp_path / ".runtime" / "scheduler.log"


def test_the_exit_file_is_the_public_constant_below_the_root(tmp_path: Path) -> None:
    assert exit_file_of(OrgPaths(tmp_path)) == tmp_path / EXIT_FILE and EXIT_FILE == ".runtime/scheduler.exit"
