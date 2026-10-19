"""All the invariants, in order, as the answer of ``IntegrityChecks.check``."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ...kernel import Clock, JsonObject, aware
from ...mail import MessageIndex
from .._ports import IntegrityCheck
from ..api import IntegrityChecks


class FileIntegrityChecks(IntegrityChecks):
    """Scans the messages once and runs each check on the scan. A new check is a new ``IntegrityCheck`` handed to the constructor."""

    def __init__(self, index: MessageIndex, checks: Sequence[IntegrityCheck], clock: Clock) -> None:
        self._index, self._checks, self._clock = index, list(checks), clock

    def check(self, now: datetime | None = None) -> JsonObject:
        at = (aware(now) or self._clock.now()).timestamp()
        files = self._index.scan()
        results = [check.run(files, at) for check in self._checks]
        return {"ok": all(c["ok"] for c in results), "checks": results}
