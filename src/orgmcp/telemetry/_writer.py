"""The open event file of one process for one organization."""

from __future__ import annotations

import threading
from collections.abc import Callable

from ..kernel import Clock, JsonObject
from ._pool import LineWriter


class FileLineWriter(LineWriter):
    def __init__(self, events_dir: str, stem: str, lock: threading.Lock) -> None:
        raise NotImplementedError("red: A-telemetry")

    def append(self, record: JsonObject, day: str, clock: Clock, retry_after: float, on_fresh: Callable[[], None]) -> None:
        raise NotImplementedError("red: A-telemetry")

    def close(self) -> None:
        raise NotImplementedError("red: A-telemetry")
