"""The legacy names of the slice are the runs package's objects (``scheduler``): one definition, many names."""

from __future__ import annotations

import orgmcp.runs as runs
from orgmcp.runs.tests._legacy import legacy


def test_the_scheduler_exports_the_id_function_of_the_package() -> None:
    assert legacy("scheduler").run_id_of is runs.run_id_of
