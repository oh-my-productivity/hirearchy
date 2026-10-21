"""The public surface: ``__init__`` re-exports exactly ``api``."""

from __future__ import annotations

import hirearchy.snapshots as snapshots
from hirearchy.snapshots import api


def test_the_package_re_exports_exactly_the_api() -> None:
    assert snapshots.__all__ == api.__all__ == ["GitClient", "IgnoreList", "OrgSnapshotter", "RUNTIME_IGNORE_LINES"]
    assert all(getattr(snapshots, name) is getattr(api, name) for name in api.__all__)


def test_the_runtime_lines_are_the_four_files_that_change_constantly() -> None:
    assert api.RUNTIME_IGNORE_LINES == (".runtime/running.json", ".runtime/scheduler.log", ".runtime/scheduler.exit", ".runtime/events/")
