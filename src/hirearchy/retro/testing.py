"""In-memory fakes of ``retro`` and the registry the contract suites iterate over.

``MemoryRetroRecords`` is the ledger of the briefs held kept in memory. The real class and the fake pass the same contract suite
(``tests/test_contract_*.py``), so a consumer's unit test may use the fake instead of a ledger on disk. Each Protocol of ``api.py`` (and the consumer
port ``CharterHistory``) gets its fake here, added by the commit that implements the Protocol.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..kernel import Clock, OrgError
from ..kernel.testing import FakeClock, ListEventSink, fs_ledger_store
from ..settings.testing import MemoryOrgSettings
from ._brief import FileRetroBriefs
from ._facts import Facts
from ._ledger import PATH, State, LedgerRetroRecords, with_record
from ._ports import CHARTER, ORG, BriefSources, CharterHistory, CharterPair, CharterVersions, ServiceRetirements
from ._views import ServiceRetired
from ._due import FileRetroDue
from .api import Brief, BriefRecord, RetroBriefs, RetroDue, RetroRecords


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


class ScriptedServiceRetirements(ServiceRetirements):
    """Answers the retired copies of services it was given."""

    def __init__(self, retired: Sequence[ServiceRetired] = ()) -> None:
        self._retired = tuple(retired)

    def retired(self) -> tuple[ServiceRetired, ...]:
        return self._retired


class FixedSources(BriefSources):
    """The facts a test put in, whatever the window: ``new`` verdicts since the last brief, the organization's ``started`` date. ``reads`` keeps the windows asked, as
    ``(since, after)``."""

    def __init__(self, facts: Facts | None = None, *, new: int = 0, started: datetime | None = None) -> None:
        self.facts = facts or Facts()
        self.new = new
        self._started = started
        self.reads: list[tuple[datetime | None, datetime | None]] = []
        self.afters: list[datetime | None] = []  # the ``after`` of each verdict count asked

    def started(self) -> datetime | None:
        return self._started

    def new_verdicts(self, after: datetime | None) -> int:
        self.afters.append(after)
        return self.new

    def read(self, since: datetime | None, after: datetime | None) -> Facts:
        self.reads.append((since, after))
        return self.facts


class FixedRetroBriefs(RetroBriefs):
    """Answers the brief it was given; ``calls`` keeps the ``since`` of each call."""

    def __init__(self, brief: Brief) -> None:
        self._brief = brief
        self.calls: list[datetime | None] = []

    def brief(self, *, since: datetime | None = None) -> Brief:
        self.calls.append(since)
        return self._brief


class FixedRetroDue(RetroDue):
    """Answers the lines it was given: ``reply`` for a reply and ``listing`` for a listing (both empty: nothing is due)."""

    def __init__(self, reply: str = "", listing: str = "") -> None:
        self._reply = reply
        self._listing = listing

    def due(self, *, listing: bool = False) -> str:
        return self._listing if listing else self._reply


@dataclass
class BriefsWorld:
    """A brief over fixed facts: the sources, the ledger (in memory), the events it emitted and the clock, for a test to prepare and to look at."""

    sources: FixedSources
    records: MemoryRetroRecords
    sink: ListEventSink
    clock: FakeClock
    briefs: RetroBriefs


def briefs_over_fixed_facts(tmp_path: Path, facts: Facts | None = None, *, new: int = 0, started: datetime | None = None, org_md: str = "---\nmission: m\n---\nrules\n") -> BriefsWorld:
    sources, records, sink, clock = FixedSources(facts, new=new, started=started), MemoryRetroRecords(), ListEventSink(), FakeClock()
    return BriefsWorld(sources, records, sink, clock, FileRetroBriefs(sources, records, MemoryOrgSettings(org_md), sink, clock))


def fixed_retro_briefs(tmp_path: Path) -> RetroBriefs:
    return FixedRetroBriefs(Brief("B1", FakeClock().now(), None, "since the organization started"))


def fs_retro_records(tmp_path: Path) -> RetroRecords:
    """The ledger over ``.runtime/retros.json`` of a directory."""
    return LedgerRetroRecords(fs_ledger_store(tmp_path).store)


def memory_retro_records(tmp_path: Path) -> RetroRecords:
    return MemoryRetroRecords()


def file_retro_briefs(tmp_path: Path) -> RetroBriefs:
    return briefs_over_fixed_facts(tmp_path).briefs


def fixed_retro_due(tmp_path: Path) -> RetroDue:
    return FixedRetroDue("Retro due: 3 verdicts of the user since the last brief (none yet). Once this delivery is settled, offer the user a retro in one line, and call retro() only after their yes.")


def file_retro_due(tmp_path: Path) -> RetroDue:
    return FileRetroDue(FixedSources(new=3), MemoryRetroRecords(), MemoryOrgSettings("---\nmission: m\n---\nrules\n"))


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    RetroRecords: [fs_retro_records, memory_retro_records],
    RetroBriefs: [file_retro_briefs, fixed_retro_briefs],
    RetroDue: [file_retro_due, fixed_retro_due],
}
