"""(e) The event files have no gaps in their line numbers."""

from __future__ import annotations

from collections.abc import Sequence

from ...eventlog import EventReader
from ...kernel import JsonObject
from ...mail import MessageFile
from .._ports import IntegrityCheck
from ._base import verdict


class SeqGapless(IntegrityCheck):
    """``seq`` counts the lines of ONE file and restarts at 1 in each day's file: every file is gapless from 1 on its own."""

    def __init__(self, events: EventReader) -> None:
        self._events = events

    def run(self, files: Sequence[MessageFile], now: float) -> JsonObject:
        problems: list[str] = []
        event_files = self._events.files()
        for f in sorted(event_files, key=lambda x: (x.day, x.path.name)):
            expect = 1
            for _, ev in self._events.read_file(f):
                seq = ev.get("seq")
                if not isinstance(seq, int) or isinstance(seq, bool):
                    continue
                if seq != expect:
                    where = f"{f.day}/{f.path.name}"
                    problems.append(f"{where}: first seq is {seq}, expected 1" if expect == 1 else
                                    f"{where}: seq jumps from {expect - 1} to {seq} ({seq - expect} line(s) lost)" if seq > expect else
                                    f"{where}: seq goes back from {expect - 1} to {seq}")
                    if len(problems) >= 50:
                        break
                expect = seq + 1
        return verdict("e", "event files have no seq gaps", problems, f"{len(event_files)} event file(s) checked")
