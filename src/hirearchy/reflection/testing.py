"""The reflection ports over files on disk and over files in memory, a fake case history, and the registry the contract suites iterate over.

``ReflectionWorld`` is what a test gets: the ports of the package built over one organization (the agents, mailboxes, services, settings and clock of
``services``' world, and the run logs of ``runs``' harness), and the means to prepare it. The run logs are stamped by the clock of the messages, so
that a window of a case contains exactly the runs a test made in it. ``FixedCaseHistory`` is the history a test puts in, for the consumers of
``CaseHistory`` (``progress``, ``dashdata``, ``prompts``); ``FixedDeliverableChecks`` the findings of a deliverable folder, for the consumers of
``DeliverableChecks`` (``progress``, ``mcp_server``). ``MemoryDeliverableFolder``, ``FixedCheckedVersions`` and ``HashBlobIds`` are the three ports
``FolderDeliverableChecks`` is built from, in memory.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from ..agents import CharterReader
from ..agents.testing import fs_agents
from ..kernel import ROOT, STAMP_FORMAT, Message, OrgError, OrgPaths
from ..runs import RunLogReader
from ..runs.testing import RunsHarness, fs_runs, memory_runs
from ..services import ServiceEvidence
from ..services.testing import ServicesWorld
from ..services.testing import fs_world as services_fs_world
from ..services.testing import memory_world as services_memory_world
from ._cases import DerivedCaseHistory
from ._deliverable_checks import FolderDeliverableChecks
from ._deliverables import FsDeliverableFolder
from ._digest import DigestBuilder
from ._evidence import CaseServiceEvidence
from ._files import OrgServicePaths
from ._ports import (
    BarChanges,
    BarHistory,
    BlobIds,
    CheckedVersions,
    DeliverableFolder,
    FolderFile,
    FolderRead,
    Located,
    RejectedServices,
    ServicePaths,
)
from ._records import DerivedCaseRecords
from ._reports import TextServiceReports
from ._runs import LogRunCounter
from ._sections import EvidenceReflectSection, MailRejectedServices, OwnedServicesListing, OwnerPromptSections, QuotedPlaybookSection, RegressionListSection
from ._steps import TextServiceSteps
from ._timeline import StorePlaybookTimelines
from .api import (
    Case,
    CaseHistory,
    CaseRecords,
    CharterMark,
    DeliverableChecks,
    DeliverableFinding,
    ModelMark,
    OwnerDeliveries,
    ReflectionDigest,
    ServicePromptSections,
    ServiceRecord,
    ServiceReports,
    ServiceSteps,
)

# ------------------------------------------------------------------------------ the fake bar histories


class NoBarHistory(BarHistory):
    """An organization with no history: nothing is known."""

    def changes(self, addrs: Sequence[str]) -> BarChanges:
        return BarChanges()


class FixedBarHistory(BarHistory):
    """The changes a test puts in, whatever the agents asked for."""

    def __init__(self, marks: Sequence[CharterMark | ModelMark] = (), *, truncated: bool = False, skipped: int = 0) -> None:
        self._found = BarChanges(known=True, marks=tuple(marks), truncated=truncated, skipped=skipped)

    def changes(self, addrs: Sequence[str]) -> BarChanges:
        return self._found


# ------------------------------------------------------------------------------ the fake records


class FixedCaseRecords(CaseRecords):
    """The records a test puts in. ``records`` answers the ones of ``service`` when it is given (an ``OrgError`` for a name none has), ``deliveries``
    the ``OwnerDeliveries`` put in for the owner (none: nothing)."""

    def __init__(self, records: Sequence[ServiceRecord] = (), deliveries: Mapping[str, OwnerDeliveries] | None = None) -> None:
        self._records = list(records)
        self._deliveries = dict(deliveries or {})

    def records(self, service: str | None = None) -> list[ServiceRecord]:
        if service is not None and not any(r.service == service for r in self._records):
            names = ", ".join(dict.fromkeys(r.service for r in self._records if r.service)) or "none"
            raise OrgError(f"no service named `{service}`: the services are {names}. Call quality() without a service for everything.")
        return [r for r in self._records if service is None or r.service == service]

    def deliveries(self, owner: str) -> OwnerDeliveries:
        return self._deliveries.get(owner, OwnerDeliveries())


# ------------------------------------------------------------------------------ the fake history


class FixedCaseHistory(CaseHistory):
    """The cases a test puts in: ``cases`` answers for the owner and service of each, ``case_of`` finds the case that holds the task."""

    def __init__(self, cases: Sequence[Case] = (), timelines: Mapping[tuple[str, str], Sequence[tuple[int, datetime]]] | None = None) -> None:
        self._cases = list(cases)
        self._timelines = {key: list(value) for key, value in (timelines or {}).items()}

    def cases(self, owner: str, service: str) -> list[Case]:
        return [c for c in self._cases if c.owner == owner and c.service == service]

    def chains(self, owner: str, service: str, *, since: datetime | None, runs: bool) -> list[Case]:
        return [c for c in self.cases(owner, service) if since is None or c.started is None or c.started >= since]

    def one_off_cases(self, *, runs: bool = True) -> list[Case]:
        return [c for c in self._cases if c.service == ""]

    def case_of(self, task: Message) -> Case | None:
        return next((c for c in self._cases if task.id in {t.id for t in c.tasks}), None)

    def playbook_timeline(self, owner: str, service: str) -> list[tuple[int, datetime]]:
        return list(self._timelines.get((owner, service), []))


class FixedDeliverableChecks(DeliverableChecks):
    """The findings a test puts in, by actor; ``findings`` answers them (only those of ``service`` when it is given, the ones marked ``settled``
    only when ``settled`` is true, and a ``given`` finding only when ``settled`` is true, whatever its own mark: the rule of the protocol)."""

    def __init__(self, findings: Mapping[str, Sequence[DeliverableFinding]] | None = None) -> None:
        self._by_actor = {actor: list(found) for actor, found in (findings or {}).items()}

    def put(self, actor: str, *found: DeliverableFinding) -> None:
        self._by_actor.setdefault(actor, []).extend(found)

    def findings(self, actor: str, service: str | None = None, *, settled: bool = False) -> list[DeliverableFinding]:
        return [
            f for f in self._by_actor.get(actor, [])
            if (settled or (not f.settled and f.kind != "given")) and (service is None or service in f.services)
        ]


class HashBlobIds(BlobIds):
    """Git's blob ids, computed here (a copy of ``snapshots.blob_id``, which ``reflection`` may not import; the test of ``app``'s ``GitBlobIds``
    compares the real one with ``git hash-object``)."""

    def of(self, data: bytes, hexlen: int) -> str:
        digest = hashlib.sha1 if hexlen == 40 else hashlib.sha256
        return digest(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def blob(data: bytes, hexlen: int = 40) -> str:
    """The blob id of ``data``, as the fakes of this module compute it."""
    return HashBlobIds().of(data, hexlen)


class MemoryDeliverableFolder(DeliverableFolder):
    """Deliverable places in memory, by absolute path: ``folder`` and ``file`` put what a read answers, ``states`` overrides what is there (``link``,
    ``unreadable``). ``reads`` and ``budgets`` record every read. A file named inside a folder that is put is a ``file`` place too."""

    def __init__(self) -> None:
        self.places: dict[str, FolderRead] = {}
        self.states: dict[str, str] = {}
        self.reads: list[str] = []
        self.budgets: list[int] = []

    def folder(self, path: str, files: Mapping[str, tuple[bytes, int]], *, used: int = 0) -> None:
        """``path`` is a folder holding ``files`` (name -> (content, last write in microseconds))."""
        listed = tuple(FolderFile(name, "file", data, stamp) for name, (data, stamp) in sorted(files.items()))
        self.places[path] = FolderRead("folder", path, listed, used=used)

    def file(self, path: str, data: bytes, mtime_us: int) -> None:
        """``path`` is a file with this content."""
        folder, _, name = path.rpartition("/")
        self.places[path] = FolderRead("file", folder, (FolderFile(name, "file", data, mtime_us),), used=len(data))

    def put(self, path: str, read: FolderRead) -> None:
        self.places[path] = read

    def locate(self, raw: object) -> Located | None:
        if not isinstance(raw, str) or not raw.startswith("/"):
            return None
        return Located(Path(raw), Path(raw))

    def kind(self, place: Located) -> str:
        return self._answer(str(place.target)).state

    def read(self, place: Located, budget: int) -> FolderRead:
        self.reads.append(str(place.target))
        self.budgets.append(budget)
        return self._answer(str(place.target))

    def _answer(self, path: str) -> FolderRead:
        if path in self.states:
            state = self.states[path]
            return FolderRead(state, path, error="Permission denied" if state == "unreadable" else "")
        if path in self.places:
            return self.places[path]
        folder, _, name = path.rpartition("/")
        found = self.places.get(folder)
        if found is not None and found.state == "folder":
            listed = next((f for f in found.files if f.name == name and f.kind == "file"), None)
            if listed is not None:  # a file named inside a folder that is there
                return FolderRead("file", folder, (listed,), used=len(listed.data))
        return FolderRead("missing", path)


class FixedCheckedVersions(CheckedVersions):
    """The team's checked versions a test puts in: ``at`` by (result id, path) -> (commit, blob id), ``now`` by path -> blob id. ``asked`` and
    ``currents`` record the questions, in order."""

    def __init__(
        self, at: Mapping[tuple[str, str], tuple[str, str]] | None = None, now: Mapping[str, str] | None = None,
        texts: Mapping[tuple[str, str], bytes] | None = None,
    ) -> None:
        self.at = dict(at or {})
        self.now = dict(now or {})
        self.texts = dict(texts or {})
        self.asked: list[tuple[str, str]] = []
        self.currents: list[tuple[str, int]] = []

    def at_result(self, result: Message, path: str) -> tuple[str, str] | None:
        self.asked.append((result.id, path))
        return self.at.get((result.id, path))

    def current(self, path: str, hexlen: int) -> str | None:
        self.currents.append((path, hexlen))
        return self.now.get(path)

    def text(self, commit: str, path: str, limit: int) -> bytes | None:
        data = self.texts.get((commit, path))
        return data if data is not None and len(data) <= limit else None


# ------------------------------------------------------------------------------ the worlds


@dataclass(frozen=True)
class ReflectionWorld:
    """The ports over one organization, and the means to prepare it. Addresses of agents: ``ceo``, ``ceo/eng``, ``ceo/qa``, ``ops``; root exists."""

    history: CaseHistory
    digest: ReflectionDigest
    reports: ServiceReports
    sections: ServicePromptSections
    steps: ServiceSteps
    rejections: RejectedServices
    evidence: ServiceEvidence  # the gate over the cases of this world (the real one: ``CaseServiceEvidence``)
    paths: ServicePaths
    s: ServicesWorld  # the organization behind the ports: services, agents, mail, settings, the clock
    runs: RunLogReader  # the run logs the history counts
    use_run: Callable[[str], None]  # the agent makes one run: a log stamped now, by the clock of the messages
    deliverables: DeliverableChecks  # the checks of the deliverable folders over this world's cases (no checked versions: git knows nothing here)
    records: CaseRecords  # the records of the cases over this world (no org history: ``NoBarHistory``)


def _world(s: ServicesWorld, runs: RunsHarness, folders: DeliverableFolder, charters: CharterReader) -> ReflectionWorld:
    d = s.d
    paths = OrgServicePaths(OrgPaths(d.root))
    history = DerivedCaseHistory(s.catalog, d.agents, d.mail, s.hints, StorePlaybookTimelines(s.store), LogRunCounter(runs.reader, d.mail), charters)
    digest = DigestBuilder(s.catalog, history)
    rejections = MailRejectedServices(d.mail)
    evidence = CaseServiceEvidence(history, s.catalog, s.store, d.mail)
    sections = OwnerPromptSections(
        s.catalog, OwnedServicesListing(s.catalog, history, paths), digest, d.mail, rejections, QuotedPlaybookSection(s.catalog, d.settings, paths, evidence),
        EvidenceReflectSection(s.catalog, d.settings, paths, history),
        RegressionListSection(s.catalog, history),
    )

    def use_run(addr: str) -> None:
        runs.add_agent(addr)
        runs.put_log(addr, f"{d.clock.now():{STAMP_FORMAT}}.log", "# run\n")

    checks = FolderDeliverableChecks(s.catalog, history, d.mail, folders, FixedCheckedVersions(), HashBlobIds(), d.clock)
    return ReflectionWorld(
        history=history, digest=digest, reports=TextServiceReports(d.agents, s.catalog, history, paths), sections=sections,
        steps=TextServiceSteps(d.agents, s.catalog, history, d.mail, evidence), rejections=rejections, evidence=evidence, paths=paths, s=s, runs=runs.reader, use_run=use_run,
        deliverables=checks, records=DerivedCaseRecords(history, s.catalog, d.agents, d.mail, s.store, NoBarHistory(), checks),
    )


def fs_world(tmp_path: Path) -> ReflectionWorld:
    return _world(services_fs_world(tmp_path), fs_runs(tmp_path), FsDeliverableFolder(), fs_agents(tmp_path).charters)


def memory_world(tmp_path: Path) -> ReflectionWorld:
    s = services_memory_world(tmp_path)
    assert isinstance(s.d.agents, CharterReader)  # the in-memory agents of the world are also its charters (``MemoryAgents``)
    return _world(s, memory_runs(tmp_path), MemoryDeliverableFolder(), s.d.agents)


def history_fs(tmp_path: Path) -> CaseHistory:
    return fs_world(tmp_path).history


def history_memory(tmp_path: Path) -> CaseHistory:
    return memory_world(tmp_path).history


def digest_fs(tmp_path: Path) -> ReflectionDigest:
    return fs_world(tmp_path).digest


def digest_memory(tmp_path: Path) -> ReflectionDigest:
    return memory_world(tmp_path).digest


def reports_fs(tmp_path: Path) -> ServiceReports:
    return fs_world(tmp_path).reports


def reports_memory(tmp_path: Path) -> ServiceReports:
    return memory_world(tmp_path).reports


def sections_fs(tmp_path: Path) -> ServicePromptSections:
    return fs_world(tmp_path).sections


def sections_memory(tmp_path: Path) -> ServicePromptSections:
    return memory_world(tmp_path).sections


def steps_fs(tmp_path: Path) -> ServiceSteps:
    return fs_world(tmp_path).steps


def steps_memory(tmp_path: Path) -> ServiceSteps:
    return memory_world(tmp_path).steps


@dataclass(frozen=True)
class DeliverableHarness:
    """A ``DeliverableChecks`` and the means to give it one finding: after ``populate``, root's ``weekly-brief`` has exactly one: ``x.md``, a file the
    team never wrote (``unknown``). ``populate_given`` is used instead of ``populate``: afterwards root's ``weekly-brief`` has exactly one finding, of
    kind ``given`` and not settled, and the task id it names is returned."""

    checks: DeliverableChecks
    populate: Callable[[], None]
    service: str
    populate_given: Callable[[], str]


SERVICE = "weekly-brief"


def deliverable_checks_fs(tmp_path: Path) -> DeliverableHarness:
    """The real checks over the fs world, with a real deliverable folder (and a ``FixedCheckedVersions`` the harness holds, for ``populate_given``)."""
    w = fs_world(tmp_path)
    folder = tmp_path / "deliverables"
    versions = FixedCheckedVersions()
    checks = FolderDeliverableChecks(w.s.catalog, w.history, w.s.d.mail, FsDeliverableFolder(), versions, HashBlobIds(), w.s.d.clock)
    memo, team = "ceo/work/memo.md", b"team v2\n"

    def write(name: str, data: bytes) -> None:
        folder.mkdir(exist_ok=True)
        written = folder / name
        written.write_bytes(data)
        later = w.s.d.clock.now() + timedelta(days=1)  # the clock of the messages is a fake: a file written "now" must be after the contract
        os.utime(written, ns=(int(later.timestamp() * 1e9),) * 2)

    def define() -> None:
        w.s.d.agent("ceo", True)
        w.s.d.agent("ceo/eng", False)
        w.s.commands.define_service(
            ROOT, "ceo", SERVICE, description="A brief.", inputs=[{"name": "topic", "description": "what", "required": True}],
            acceptance=["At most 600 words"], deliverable={"description": "one markdown file", "path": str(folder)}, budget=10,
        )

    def answer(task: Message, status: str) -> Message:
        body = f"## Summary\nok\n\n## Artifacts\n- {memo} (3 words)\n"
        return w.s.d.post(Message(sender=task.to, to=task.sender, type="result", status=status, reply_to=task.id, body=body, title="Result"))

    def populate() -> None:
        define()
        write("x.md", b"somebody's file\n")

    def populate_given() -> str:
        """The m0-s2 shape (design 4.8): the head ``a`` is reported blocked, the user's rework ``b`` is delivered with v2, the head's late result lists
        the same file, the user accepts ``a``'s late delivery and only then copies the file (v2): it equals ``a`` and ``b``, and ``b`` is the latest."""
        define()
        head = w.s.commands.request(ROOT, SERVICE, {"topic": "ai"})
        answer(head, "blocked")
        rework = w.s.commands.request(ROOT, SERVICE, {"topic": "ai"}, revises=head.id, source="human")
        versions.at[(answer(rework, "done").id, memo)] = ("c1", blob(team))
        versions.at[(answer(head, "done").id, memo)] = ("c1", blob(team))
        w.s.commands.feedback(ROOT, head.id, "accept", "", source="human")
        write("memo.md", team)
        return head.id

    return DeliverableHarness(checks, populate, SERVICE, populate_given)


def deliverable_checks_fixed(tmp_path: Path) -> DeliverableHarness:
    fixed = FixedDeliverableChecks()
    finding = DeliverableFinding(folder=str(tmp_path / "deliverables"), services=(SERVICE,), name="x.md", kind="unknown")
    given = DeliverableFinding(folder=str(tmp_path / "deliverables"), services=(SERVICE,), name="memo.md", kind="given", task="20261018T100000000000-root-0000")

    def populate_given() -> str:
        fixed.put(ROOT, given)
        return given.task

    return DeliverableHarness(fixed, lambda: fixed.put(ROOT, finding), SERVICE, populate_given)


@dataclass(frozen=True)
class RecordsHarness:
    """A ``CaseRecords`` and the means to prepare it. After ``populate`` root's ``weekly-brief``, offered by ``ceo``, has one record with a case
    (``ceo`` has the delivery); ``corrupt`` then makes that service unreadable (its stored contract versions do not parse)."""

    records: CaseRecords
    populate: Callable[[], None]
    corrupt: Callable[[], None]
    owner: str
    service: str


def records_fs(tmp_path: Path) -> RecordsHarness:
    return _records_world(fs_world(tmp_path))


def records_memory(tmp_path: Path) -> RecordsHarness:
    return _records_world(memory_world(tmp_path))


def _records_world(w: ReflectionWorld) -> RecordsHarness:
    def populate() -> None:
        w.s.d.agent("ceo", True)
        w.s.d.agent("ceo/eng", False)
        w.s.commands.define_service(
            ROOT, "ceo", SERVICE, description="A brief.", inputs=[{"name": "topic", "description": "what", "required": True}],
            acceptance=["At most 600 words"], deliverable={"description": "one markdown file"}, budget=10,
        )
        task = w.s.commands.request(ROOT, SERVICE, {"topic": "ai"})
        w.s.d.post(Message(sender=task.to, to=task.sender, type="result", status="done", reply_to=task.id, body="Delivered.", title="Result"))

    def corrupt() -> None:
        w.s.put(f"ceo/services/{SERVICE}/SERVICE.md", "---\nkey: [unclosed\n---\n")

    return RecordsHarness(w.records, populate, corrupt, "ceo", SERVICE)


def records_fixed(tmp_path: Path) -> RecordsHarness:
    one_off = ServiceRecord("", "", ROOT, "human")
    held = {"records": FixedCaseRecords([one_off])}  # an empty organization: root's one-off record only

    class Switch(CaseRecords):
        """The fixed records a harness can swap, so that ``populate`` and ``corrupt`` change what it answers."""

        def records(self, service: str | None = None) -> list[ServiceRecord]:
            return held["records"].records(service)

        def deliveries(self, owner: str) -> OwnerDeliveries:
            return held["records"].deliveries(owner)

    case = Case(
        id="c1", service=SERVICE, owner="ceo", tasks=[], result=None, state="open", playbook=0, used=0, reworks=0, budget=10, runs=0, lessons=[],
        verdicts=[], started=None, finished=None,
    )
    good = ServiceRecord("ceo", SERVICE, ROOT, "human", contract=1, budget=10, cases=(case,))
    bad = ServiceRecord("ceo", SERVICE, ROOT, "human", error="the stored contract versions: does not parse (ScannerError)")

    def populate() -> None:
        held["records"] = FixedCaseRecords([good, one_off])

    def corrupt() -> None:
        held["records"] = FixedCaseRecords(
            [bad, one_off], {"ceo": OwnerDeliveries(unknown=f"{SERVICE}: the stored contract versions: does not parse (ScannerError)")},
        )

    return RecordsHarness(Switch(), populate, corrupt, "ceo", SERVICE)


PURE = {"StatsReport"}  # data with derived views (counts that print themselves): one implementation, no fake

IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    CaseHistory: [history_fs, history_memory],
    ReflectionDigest: [digest_fs, digest_memory],
    ServiceReports: [reports_fs, reports_memory],
    ServicePromptSections: [sections_fs, sections_memory],
    ServiceSteps: [steps_fs, steps_memory],
    DeliverableChecks: [deliverable_checks_fs, deliverable_checks_fixed],
    CaseRecords: [records_fs, records_fixed],
}
