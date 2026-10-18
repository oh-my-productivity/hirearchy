"""The traces delivered by a tool call, collected in its thread."""

from __future__ import annotations

from contextlib import AbstractContextManager

from ..kernel import TraceTap
from .api import TraceScope


class ThreadLocalTraceScope(TraceScope, TraceTap):
    def __init__(self) -> None:
        raise NotImplementedError("red: A-telemetry")

    def collect(self) -> AbstractContextManager[list[str | None]]:
        raise NotImplementedError("red: A-telemetry")

    def note(self, trace: str | None) -> None:
        raise NotImplementedError("red: A-telemetry")
