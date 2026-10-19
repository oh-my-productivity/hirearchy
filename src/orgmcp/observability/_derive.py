"""The trace of every message, derived from the files. (RED: skeleton.)"""

from __future__ import annotations

from collections.abc import Mapping

from ..runs import RunLogReader
from ._messages import Msg
from ._ports import TraceDeriver, TraceDerivers


class MessageTraceDeriver(TraceDeriver):
    def __init__(self, msgs: Mapping[str, Msg], batches: Mapping[str, list[str]] | None, logs: RunLogReader) -> None:
        self._msgs, self._batches, self._logs = msgs, batches, logs

    def of(self, mid: str) -> tuple[str | None, str]:
        raise NotImplementedError("red: C-obs-1")


class LogTraceDerivers(TraceDerivers):
    def __init__(self, logs: RunLogReader) -> None:
        self._logs = logs

    def derive(self, msgs: Mapping[str, Msg], batches: Mapping[str, list[str]] | None = None) -> TraceDeriver:
        raise NotImplementedError("red: C-obs-1")
