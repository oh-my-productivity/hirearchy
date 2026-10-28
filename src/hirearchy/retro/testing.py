"""In-memory fakes of ``retro`` and the registry the contract suites iterate over.

``MemoryRetroRecords`` is the ledger of the briefs held kept in memory. The real class and the fake pass the same contract suite
(``tests/test_contract_*.py``), so a consumer's unit test may use the fake instead of a ledger on disk. Each Protocol of ``api.py`` (and the consumer
port ``CharterHistory``) gets its fake here, added by the commit that implements the Protocol.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from ..kernel import OrgError
from ..kernel.testing import fs_ledger_store
from ._ledger import PATH, State, LedgerRetroRecords, with_record
from .api import BriefRecord, RetroRecords


class MemoryRetroRecords(RetroRecords):
    """The ledger kept in memory. ``unreadable`` (a reason) makes the readers raise ``OrgError`` until the next ``append`` replaces it; ``unwritable``
    makes ``append`` raise ``OrgError`` and keep what it held."""

    def __init__(self) -> None:
        self._state: State = ((), ())
        self.unreadable = ""
        self.unwritable = ""

    def _read(self) -> State:
        if self.unreadable:
            raise OrgError(f"{PATH} is not a record of briefs ({self.unreadable})")
        return self._state

    def last(self) -> BriefRecord | None:
        briefs = self._read()[0]
        return briefs[-1] if briefs else None

    def records(self) -> tuple[BriefRecord, ...]:
        return self._read()[0]

    def asked(self) -> frozenset[str]:
        return frozenset(self._read()[1])

    def append(self, record: BriefRecord) -> None:
        if self.unwritable:
            raise OrgError(f"{PATH} cannot be written: {self.unwritable}")
        self._state = with_record(((), ()) if self.unreadable else self._state, record)
        self.unreadable = ""


def fs_retro_records(tmp_path: Path) -> RetroRecords:
    """The ledger over ``.runtime/retros.json`` of a directory."""
    return LedgerRetroRecords(fs_ledger_store(tmp_path).store)


def memory_retro_records(tmp_path: Path) -> RetroRecords:
    return MemoryRetroRecords()


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    RetroRecords: [fs_retro_records, memory_retro_records],
}
