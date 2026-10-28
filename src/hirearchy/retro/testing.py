"""In-memory fakes of ``retro`` and the registry the contract suites iterate over.

``MemoryRetroRecords`` is the ledger of the briefs held kept in memory. The real class and the fake pass the same contract suite
(``tests/test_contract_*.py``), so a consumer's unit test may use the fake instead of a ledger on disk. Each Protocol of ``api.py`` (and the consumer
port ``CharterHistory``) gets its fake here, added by the commit that implements the Protocol.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path

from ..kernel import OrgError
from ..kernel.testing import fs_ledger_store
from ._ledger import PATH, State, LedgerRetroRecords, with_record
from ._ports import ORG, CHARTER, CharterHistory, CharterPair, CharterVersions
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


class ScriptedCharterHistory(CharterHistory):
    """Answers the pairs, subjects and start it was given: ``versions`` returns the pairs of the agents asked for and of ``ORG.md`` in the order given
    (newest first), with ``truncated`` and ``skipped`` as set; ``known=False`` is a history that does not exist. ``calls`` keeps what it was asked."""

    def __init__(
        self, pairs: Sequence[CharterPair] = (), *, known: bool = True, truncated: bool = False, skipped: int = 0, subjects: Mapping[str, str] | None = None,
        started: datetime | None = None,
    ) -> None:
        self._pairs = tuple(pairs)
        self._known = known
        self._truncated = truncated
        self._skipped = skipped
        self._subjects = dict(subjects or {})
        self._started = started
        self.calls: list[tuple[str, ...]] = []

    def versions(self, addrs: Sequence[str]) -> CharterVersions:
        self.calls.append(("versions", *addrs))
        if not self._known:
            return CharterVersions(known=False)
        paths = {f"{addr}/{CHARTER}" for addr in addrs} | {ORG}
        return CharterVersions(True, tuple(p for p in self._pairs if p.path in paths), self._truncated, self._skipped)

    def subject(self, commit: str) -> str | None:
        self.calls.append(("subject", commit))
        return self._subjects.get(commit) if self._known else None

    def org_started(self) -> datetime | None:
        self.calls.append(("org_started",))
        return self._started if self._known else None


def fs_retro_records(tmp_path: Path) -> RetroRecords:
    """The ledger over ``.runtime/retros.json`` of a directory."""
    return LedgerRetroRecords(fs_ledger_store(tmp_path).store)


def memory_retro_records(tmp_path: Path) -> RetroRecords:
    return MemoryRetroRecords()


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    RetroRecords: [fs_retro_records, memory_retro_records],
}
