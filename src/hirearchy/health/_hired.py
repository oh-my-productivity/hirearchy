"""``CharterHireDates``: when an agent was hired, for agents that never did anything (their quiet time starts then)."""

from __future__ import annotations

from datetime import datetime

from ..agents import CharterReader
from ..kernel import parse_time
from ._ports import CharterStamp, HireDates


class CharterHireDates(HireDates):
    def __init__(self, charters: CharterReader, stamps: CharterStamp) -> None:
        self._charters = charters
        self._stamps = stamps

    def hired(self, addr: str) -> datetime:
        hired = parse_time(self._charters.charter(addr)[0].get("created"))
        if hired is None:
            hired = self._stamps.modified(addr)
        return hired
