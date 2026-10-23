"""The launcher's read-only tool ids equal observability's read-only tools (phase 0a.2, design 9.1).

The launcher (``kiro/_launch.py``) imports only the standard library, so it cannot read ``observability``'s ``READ_ONLY_TOOLS``; this pins the copy.
``R2`` binds the packages under ``src/``, not these tests, which may import a private module."""

from __future__ import annotations

from hirearchy.kiro._launch import READ_ONLY_TOOL_IDS
from hirearchy.observability._trace import READ_ONLY_TOOLS


def test_read_only_tool_ids_equal_observability_read_only_tools() -> None:
    assert READ_ONLY_TOOL_IDS == tuple(sorted("hirearchy::" + tool for tool in READ_ONLY_TOOLS))
