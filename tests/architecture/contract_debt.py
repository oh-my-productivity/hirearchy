"""Protocols whose contract suite (rule R8) is owed by a later step, and which step.

A Protocol in an ``api.py`` needs ``tests/test_contract_<snake_name>.py`` and a real + fake entry in ``testing.IMPLEMENTATIONS``. A
port that lives in the kernel but whose real implementation is written by a later feature step (``EventSink``/``TraceTap``: the
real ones are ``telemetry``'s) cannot have its suite earlier. Such a Protocol is listed here as ``"<package>.<Protocol>": "<step>"``.

The list only shrinks: ``checks.contract_suites`` ignores a listed Protocol while its suite is missing and FAILS as soon as the
suite exists (the step that adds it deletes the entry). An entry for a Protocol that does not exist yet is harmless.
"""

from __future__ import annotations

PENDING: dict[str, str] = {
    "kernel.EventSink": "A-telemetry",  # real FsEventSink is written there; kernel has the port and a recording fake
    "kernel.TraceTap": "A-telemetry",  # real ThreadLocalTraceScope is written there
}
