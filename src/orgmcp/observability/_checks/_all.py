"""All the invariants, in order, as the answer of ``IntegrityChecks.check``."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ...kernel import Clock, JsonObject
from ...mail import MessageIndex
from .._ports import IntegrityCheck
from ..api import IntegrityChecks


class FileIntegrityChecks(IntegrityChecks):
    def __init__(self, index: MessageIndex, checks: Sequence[IntegrityCheck], clock: Clock) -> None:
        self._index, self._checks, self._clock = index, list(checks), clock

    def check(self, now: datetime | None = None) -> JsonObject:
        raise NotImplementedError("red: C-obs-2")
