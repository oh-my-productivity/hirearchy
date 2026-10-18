"""The traces delivered by a tool call, collected in its thread."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager

from ..kernel import TraceTap
from .api import TraceScope


class ThreadLocalTraceScope(TraceScope, TraceTap):
    """The collection is per thread: a delivery made in another thread (the ``progress`` tool works in a worker thread) is not collected by
    the block of the calling thread. This is how it always was and it is kept (ARCHITECTURE.md 10.1, risk 12)."""

    def __init__(self) -> None:
        self._local = threading.local()

    def collect(self) -> AbstractContextManager[list[str | None]]:
        return self._collect()

    @contextmanager
    def _collect(self) -> Iterator[list[str | None]]:
        previous = getattr(self._local, "seen", None)
        seen: list[str | None] = []
        self._local.seen = seen
        try:
            yield seen
        finally:
            self._local.seen = previous

    def note(self, trace: str | None) -> None:
        seen = getattr(self._local, "seen", None)
        if seen is not None:
            seen.append(trace)
