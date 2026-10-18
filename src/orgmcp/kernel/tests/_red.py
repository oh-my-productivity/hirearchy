"""Step K1 only: which implementations are still red while the step is being built (deleted when all are green)."""

from __future__ import annotations

import pytest

from orgmcp.kernel.testing import IMPLEMENTATIONS

RED: frozenset[str] = frozenset({
    "system_clock", "fake_clock", "timestamp_id_generator", "sequence_id_generator", "list_event_sink",
    "recording_trace_tap", "fs_atomic_writer", "memory_atomic_writer", "fs_ledger_store", "memory_ledger_store",
    "os_environment", "dict_environment",
})


def impls(protocol: type) -> list[object]:
    """The registered implementations of ``protocol`` as pytest params; those in ``RED`` are strict xfails."""
    red = pytest.mark.xfail(strict=True, reason="red: K1")
    return [
        pytest.param(factory, id=factory.__name__, marks=red if factory.__name__ in RED else ())
        for factory in IMPLEMENTATIONS[protocol]
    ]
