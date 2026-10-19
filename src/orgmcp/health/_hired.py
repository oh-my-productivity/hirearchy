"""``CharterHireDates``: when an agent was hired, for agents that never did anything (their quiet time starts then)."""

from __future__ import annotations

from datetime import datetime

from ..agents import CharterReader
from ._ports import CharterStamp, HireDates


class CharterHireDates(HireDates):
    def __init__(self, charters: CharterReader, stamps: CharterStamp) -> None:
        pass  # red: C-health

    def hired(self, addr: str) -> datetime:
        raise NotImplementedError("red: C-health")
