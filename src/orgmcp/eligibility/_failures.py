"""``LedgerFailureCounter``: the consecutive failures of each agent in ``.runtime/failures.json``."""

from __future__ import annotations

from ..kernel import LedgerStore
from ._ports import LedgerShape
from .api import FailureCounter


class LedgerFailureCounter(FailureCounter):
    def __init__(self, ledgers: LedgerStore, shape: LedgerShape) -> None:
        raise NotImplementedError("red: B-eligibility")

    def record(self, addr: str) -> int:
        raise NotImplementedError("red: B-eligibility")

    def clear(self, addr: str) -> None:
        raise NotImplementedError("red: B-eligibility")

    def repair(self) -> bool:
        raise NotImplementedError("red: B-eligibility")
