"""The services over files on disk and over files in memory, the fake store, and the registry the contract suites iterate over.

``MemoryServiceStore`` is the in-memory ``ServiceStore``: it keeps the text of every file under the path the real store would use, so that it round
trips through the same frontmatter and answers like the real one. ``ServicesWorld`` is what a test gets: the ports of the package built over one
organization (the agents, mailboxes, message sender, settings and clock of ``dispatch``'s world), the events they emitted, and the means to look at
the files.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from fnmatch import fnmatch
from pathlib import Path

from ..agents import AgentDirectory, RetiredArchive, RetiredTree
from ..agents.testing import fs_agents
from ..delivery import MessageDelivery
from ..dispatch import MessageSender, ReworkContext
from ..dispatch.testing import MEMORY_ROOT, DispatchWorld, PostedDelivery
from ..dispatch.testing import fs_world as dispatch_fs_world
from ..dispatch.testing import memory_world as dispatch_memory_world
from ..kernel import ROOT, AtomicWriter, JsonObject, Message, OrgError, OrgPaths, join_frontmatter, norm, split_frontmatter
from ..kernel.testing import ListEventSink, fs_atomic_writer
from ..mail import MailboxReader
from ._amend import ContractAmender
from ._catalog import ContractServiceCatalog
from ._commands import RuleServiceCommands
from ._continue import RecordedContinuations
from ._define import RuleContractDefiner
from ._feedback import RuleClientFeedback, SenderLinkNotes
from ._hints import ServiceReportHints
from ._normalizer import TextContractNormalizer
from ._parse import FILE_SHAPE, as_int, merged_versions
from ._places import OrgServicePlaces
from ._playbook import RulePlaybookReviser
from ._protocols import ContinuedServices, LinkNotes, RetiredService, ServiceFiles, ServicePlaces, ServiceRequests, ServiceRestorer
from ._request import RuleServiceRequester, TextRequestBodies
from ._retire import RuleServiceRetirement
from ._rework import ServiceReworkContext
from ._store import FsServiceStore, OsServiceFiles
from ._texts import CappedPlaybookTexts, DirectReportOwners, EventedPlaybookWriter
from .api import (
    Admission,
    AmendmentBasis,
    CaseAllowance,
    ContractNormalizer,
    JudgedBase,
    JudgedVersions,
    ServiceCatalog,
    ServiceCommands,
    ServiceEvidence,
    ServiceHints,
    ServiceStore,
    normalize_evidence,
    normalize_links,
)

# ------------------------------------------------------------------------------ the fake store


class MemoryServiceStore(ServiceStore, ServiceRestorer):
    """The files of the services in a dictionary (``files``: path -> text), laid out like the real store lays them out."""

    def __init__(self, places: ServicePlaces) -> None:
        self._places = places
        self.files: dict[Path, str] = {}

    def names(self, owner: str) -> list[str]:
        if norm(owner) == ROOT:
            return []
        directory = self._places.services_dir(owner)
        found = {p.parent.name for p in self.files if p.name == "SERVICE.md" and p.parent.parent == directory}
        return sorted(n for n in found if not n.startswith("."))

    def read_contract(self, owner: str, name: str) -> tuple[JsonObject, str] | None:
        return self._read(self._places.contract_file(owner, name))

    def read_playbook(self, owner: str, name: str) -> tuple[JsonObject, str] | None:
        return self._read(self._places.playbook_file(owner, name))

    def write_contract(self, owner: str, name: str, meta: JsonObject, body: str, archive_version: int | None) -> str:
        path = self._places.contract_file(owner, name)
        if archive_version is not None:
            self.files[self._places.history_file(owner, name, "SERVICE", archive_version)] = self.files[path]
        self.files[path] = join_frontmatter(meta, body)
        return self._places.rel(path)

    def write_playbook(
        self, owner: str, name: str, version: int, meta: JsonObject, body: str, archive_version: int | None = None,
    ) -> str:
        path = self._places.playbook_file(owner, name)
        if archive_version is not None:
            self.files[self._places.history_file(owner, name, "PLAYBOOK", archive_version)] = self.files[path]
        self.files[path] = join_frontmatter(meta, body)
        return self._places.rel(path)

    def restore(self, owner: str, name: str, retired: RetiredService) -> None:
        directory = self._places.service_dir(owner, name)
        shapes = [(rel, text) for rel, text in retired.files if FILE_SHAPE.fullmatch(rel)]
        for rel, text in sorted(shapes, key=lambda file: file[0] == "SERVICE.md"):  # SERVICE.md last
            self.files[directory / rel] = text

    def retire(self, owner: str, name: str, stamp: str) -> str:
        source, dest = self._places.service_dir(owner, name), self._places.retired_dir(owner, name, stamp)
        for path in [p for p in self.files if source in p.parents]:
            self.files[dest / path.relative_to(source)] = self.files.pop(path)
        return self._places.rel(dest)

    def playbook_history(self, owner: str, name: str) -> list[tuple[int, JsonObject]]:
        directory = self._places.service_dir(owner, name) / "history"
        paths = [*sorted(p for p in self.files if p.parent == directory and fnmatch(p.name, "PLAYBOOK.v*.md")), self._places.playbook_file(owner, name)]
        found: list[tuple[int, JsonObject]] = []
        for path in paths:
            if path in self.files:
                meta = split_frontmatter(self.files[path])[0]
                found.append((as_int(meta.get("version")), meta))
        return found

    def versions(self, owner: str, name: str, kind: str) -> list[tuple[int, JsonObject, str]]:
        merged_versions(kind, [])  # the kind is checked before any file is read
        directory = self._places.service_dir(owner, name) / "history"
        paths = [*sorted(p for p in self.files if p.parent == directory and fnmatch(p.name, f"{kind}.v*.md")), self._places.service_dir(owner, name) / f"{kind}.md"]
        return merged_versions(kind, [split_frontmatter(self.files[p]) for p in paths if p in self.files])

    def _read(self, path: Path) -> tuple[JsonObject, str] | None:
        return split_frontmatter(self.files[path]) if path in self.files else None


class MemoryServiceFiles(ServiceFiles):
    """The files of the copies the continuation reads, kept in the dictionary of a ``MemoryServiceStore`` (``mark_unreadable`` makes one fail)."""

    def __init__(self, files: Mapping[Path, str]) -> None:
        self._files = files
        self._unreadable: set[Path] = set()

    def mark_unreadable(self, path: Path) -> None:
        self._unreadable.add(path)

    def listdir(self, path: Path) -> list[str]:
        return sorted({p.relative_to(path).parts[0] for p in self._files if path in p.parents})

    def read_text(self, path: Path) -> str | None:
        if path in self._unreadable:
            raise OSError(f"{path} cannot be read")
        return self._files.get(path)


class MemoryRetiredTrees(RetiredArchive):
    """The retired trees of an organization whose files are the dictionary of a ``MemoryServiceStore``: the directories below ``.retired``."""

    def __init__(self, root: Path, files: Mapping[Path, str]) -> None:
        self._base = root / ".retired"
        self._files = files

    def trees(self) -> list[RetiredTree]:
        named = [RetiredTree(n, False, self._base / n) for n in sorted({p.relative_to(self._base).parts[0] for p in self._files if self._base in p.parents})]
        return [replace(t, top_level="/" not in t.addr) for t in named]

    def run_count(self) -> int:
        return 0

    def unspent_budget(self, tree: RetiredTree) -> int:
        return 0

    def credited(self) -> int:
        return 0


# ------------------------------------------------------------------------------ the stand-ins for the evidence gate


class AdmittingServiceEvidence(ServiceEvidence):
    """The gate that lets everything through: admits every revision by rule ``b`` and accepts every link (the ids normalized). The default of the
    worlds: the tests of the commands that call the gate do not need its judgement, ``reflection`` has the real one. ``confirmed`` are the criterion
    ids it says the client confirmed (none by default); ``basis`` is the record it says the service has (no rejection, no delivery without a
    verdict, by default)."""

    def __init__(self, confirmed: Iterable[str] = (), basis: AmendmentBasis | None = None) -> None:
        self._confirmed = frozenset(confirmed)
        self._basis = basis or AmendmentBasis((), ())

    def confirmed(self, owner: str, service: str) -> frozenset[str]:
        return self._confirmed

    def amendment_basis(self, owner: str, service: str) -> AmendmentBasis:
        return self._basis

    def links(self, owner: str, service: str, ids: Sequence[str], *, verdict: str | None = None) -> tuple[str, ...]:
        return normalize_links(list(ids))

    def admit(
        self, owner: str, service: str, evidence: Sequence[str], reason: str, *, exempt: str | None = None, lines: Sequence[str] = (),
    ) -> Admission:
        ids = normalize_evidence(list(evidence))
        if exempt:
            return Admission(exempt, ids, "no evidence needed")
        admitting = ids[0] if ids else "b"  # every line rests on the first id it cites
        return Admission("b", ids, "admitted by the stand-in for the gate", lines=tuple((admitting, line) for line in lines))


class RefusingServiceEvidence(AdmittingServiceEvidence):
    """The gate that refuses every revision that is not exempt, with the text it was given (the links as the admitting one)."""

    def __init__(self, text: str = "refused by the stand-in for the gate", basis: AmendmentBasis | None = None) -> None:
        super().__init__((), basis)
        self._text = text

    def admit(
        self, owner: str, service: str, evidence: Sequence[str], reason: str, *, exempt: str | None = None, lines: Sequence[str] = (),
    ) -> Admission:
        if exempt:
            return super().admit(owner, service, evidence, reason, exempt=exempt, lines=lines)
        raise OrgError(self._text)


# ------------------------------------------------------------------------------ the stand-ins for a write that fails


class FlakyLinkNotes(LinkNotes):
    """The link writer that fails its first ``failures`` calls with ``error`` and writes through ``inner`` afterwards (a link that cannot be written)."""

    def __init__(self, inner: LinkNotes, failures: int = 1, error: Exception | None = None) -> None:
        self._inner = inner
        self._failures = failures
        self._error = error or OSError("disk full")

    def write(self, actor: str, owner: str, title: str, rejection: str, ids: Sequence[str], words: str, source: str | None = "human") -> Message:
        if self._failures > 0:
            self._failures -= 1
            raise self._error
        return self._inner.write(actor, owner, title, rejection, ids, words, source)


class FlakyDelivery(MessageDelivery):
    """The delivery whose notes of the runtime fail the first ``failures`` times with ``error`` (messages themselves go through ``inner``)."""

    def __init__(self, inner: MessageDelivery, failures: int = 1, error: Exception | None = None) -> None:
        self._inner = inner
        self._failures = failures
        self._error = error or OSError("disk full")

    def deliver(self, msg: Message) -> Message:
        return self._inner.deliver(msg)

    def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
        if self._failures > 0:
            self._failures -= 1
            raise self._error
        return self._inner.notify(to, title, body, wake, trace)


# ------------------------------------------------------------------------------ the worlds


@dataclass(frozen=True)
class StoreHarness:
    """A store and the means to look at its files."""

    store: ServiceStore
    places: ServicePlaces
    text: Callable[[str], str | None]  # the text of a file (path relative to the organization), None when there is none
    rels: Callable[[], list[str]]  # every file of the services, relative to the organization, sorted
    restorer: ServiceRestorer  # the store, as the port that puts a retired copy back
    files: ServiceFiles  # the files of the retired copies, as the continuation reads them
    archive: RetiredArchive  # the retired trees of the organization
    put: Callable[[str, str], None]  # a file with this text at this path (relative to the organization); the directories above it are made
    unreadable: Callable[[str], None]  # the file at this path (relative to the organization) cannot be read any more


@dataclass(frozen=True)
class ServicesWorld:
    """The ports over one organization, and the means to prepare and inspect it. Addresses of agents: ``ceo``, ``ceo/eng``, ...; root exists."""

    commands: ServiceCommands
    catalog: ServiceCatalog
    store: ServiceStore
    hints: ServiceHints
    evidence: ServiceEvidence  # the gate the commands that need one are built with (the admitting stand-in unless the test chose another)
    normalizer: ContractNormalizer
    rework: ReworkContext
    places: ServicePlaces
    d: DispatchWorld  # the organization behind the ports: agents, mail, the sender, settings, the clock
    events: ListEventSink  # what the commands emitted
    text: Callable[[str], str | None]  # the text of a file (path relative to the organization), None when there is none
    rels: Callable[[], list[str]]  # every file of the services, relative to the organization, sorted
    continued: ContinuedServices  # the retired copies the definer continues (the world's, built over its files, archive and mailboxes)
    put: Callable[[str, str], None]  # a file with this text at this path (relative to the organization); the directories above it are made
    unreadable: Callable[[str], None]  # the file at this path (relative to the organization) cannot be read any more


def _text_on_disk(root: Path) -> Callable[[str], str | None]:
    def text(rel: str) -> str | None:
        path = root / rel
        return path.read_text(encoding="utf-8") if path.is_file() else None

    return text


def _rels_on_disk(root: Path) -> Callable[[], list[str]]:
    def rels() -> list[str]:
        return sorted(str(p.relative_to(root)) for p in root.glob("**/services/**/*.md"))

    return rels


def fs_store(tmp_path: Path, writer: Callable[[AtomicWriter], AtomicWriter] | None = None) -> StoreHarness:
    """The store on disk; ``writer`` wraps the atomic writer it writes through (a write that fails, a write that is watched)."""
    places = OrgServicePlaces(OrgPaths(tmp_path))
    atomic = fs_atomic_writer(tmp_path).writer
    store = FsServiceStore(places, writer(atomic) if writer else atomic)

    def put(rel: str, text: str) -> None:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def unreadable(rel: str) -> None:
        (tmp_path / rel).write_bytes(b"\xff\xfe not text")  # not UTF-8

    return StoreHarness(
        store, places, _text_on_disk(tmp_path), _rels_on_disk(tmp_path), store, OsServiceFiles(), fs_agents(tmp_path).archive, put, unreadable,
    )


def memory_store(tmp_path: Path) -> StoreHarness:
    places = OrgServicePlaces(OrgPaths(MEMORY_ROOT))
    store = MemoryServiceStore(places)
    files = MemoryServiceFiles(store.files)

    def text(rel: str) -> str | None:
        return store.files.get(MEMORY_ROOT / rel)

    def rels() -> list[str]:
        return sorted(str(p.relative_to(MEMORY_ROOT)) for p in store.files)

    def put(rel: str, content: str) -> None:
        store.files[MEMORY_ROOT / rel] = content

    return StoreHarness(
        store, places, text, rels, store, files, MemoryRetiredTrees(MEMORY_ROOT, store.files), put, lambda rel: files.mark_unreadable(MEMORY_ROOT / rel),
    )


def _world(
    d: DispatchWorld, harness: StoreHarness, evidence: ServiceEvidence | None = None, links: Callable[[LinkNotes], LinkNotes] | None = None,
    delivery: Callable[[MessageDelivery], MessageDelivery] | None = None, judged: JudgedVersions | None = None,
    allowance: CaseAllowance | None = None,
) -> ServicesWorld:
    """``links`` and ``delivery`` wrap the link writer and the delivery of the runtime's notes (a write that fails, a call that is watched);
    ``judged`` is the base a human rework is checked against (``NoJudgedVersions``: none needs one); ``allowance`` is what is left of a case's approved
    runs (``FixedAllowance({})``: every answer None, so a rework gets the contract's budget, as before 0a.3)."""
    places, store = harness.places, harness.store
    gate = evidence or AdmittingServiceEvidence()
    link_notes: LinkNotes = SenderLinkNotes(d.sender)
    link_notes = links(link_notes) if links else link_notes
    events, posted = ListEventSink(), PostedDelivery(d.post)
    notes: MessageDelivery = delivery(posted) if delivery else posted
    normalizer = TextContractNormalizer()
    catalog = ContractServiceCatalog(store, d.agents, places)
    owners, texts = DirectReportOwners(d.agents), CappedPlaybookTexts(d.settings)
    playbooks = EventedPlaybookWriter(store, d.clock, events)
    continued = RecordedContinuations(places, harness.archive, d.mail, harness.files)
    commands = RuleServiceCommands(
        RuleContractDefiner(
            d.agents, catalog, store, places, normalizer, ContractAmender(), texts, owners, playbooks, notes, d.clock, events, gate, link_notes,
            continued, harness.restorer,
        ),
        RuleServiceRetirement(d.agents, catalog, store, owners, notes, d.clock, events, gate),
        RulePlaybookReviser(d.agents, catalog, texts, playbooks, notes, gate),
        RuleServiceRequester(
            d.agents, catalog, d.mail, TextRequestBodies(), d.sender, judged or NoJudgedVersions(), allowance or FixedAllowance({}), gate, store,
        ),
        RuleClientFeedback(d.agents, d.mail, d.sender, gate, store),
    )
    return ServicesWorld(
        commands=commands, catalog=catalog, store=store, hints=ServiceReportHints(catalog), evidence=gate,
        normalizer=normalizer,
        rework=ServiceReworkContext(d.mail, d.agents, catalog), places=places, d=d, events=events, text=harness.text, rels=harness.rels,
        continued=continued, put=harness.put, unreadable=harness.unreadable,
    )


def unheld_requests(
    agents: AgentDirectory, catalog: ServiceCatalog, mail: MailboxReader, sender: MessageSender, judged: JudgedVersions, allowance: CaseAllowance,
    store: ServiceStore,
) -> ServiceRequests:
    """A requester over the given ports that judges a new request against the record of an organization with no rejection (the admitting stand-in):
    clause 2's REQUEST-UNANSWERED does not hold it. For the tests of another rule, which need a rejection with no answer and a new request in the
    same story (a prompt that shows both); the tests of REQUEST-UNANSWERED call the real commands."""
    return RuleServiceRequester(agents, catalog, mail, TextRequestBodies(), sender, judged, allowance, AdmittingServiceEvidence(), store)


def unheld_request(w: ServicesWorld, actor: str, service: str, inputs: Mapping[str, object] | None, **kw: object) -> Message:
    """``actor``'s new request of ``service`` through the world's own ports, not held by clause 2 (see :func:`unheld_requests`)."""
    requester = unheld_requests(w.d.agents, w.catalog, w.d.mail, w.d.sender, NoJudgedVersions(), FixedAllowance({}), w.store)
    given: dict[str, object] = {"title": "", "note": "", "extra_acceptance": None, "budget": None, "revises": None, "source": None, "base": None, **kw}
    return requester.request(actor, service, inputs, **given)  # type: ignore[arg-type]


def fs_world(
    tmp_path: Path, evidence: ServiceEvidence | None = None, links: Callable[[LinkNotes], LinkNotes] | None = None,
    delivery: Callable[[MessageDelivery], MessageDelivery] | None = None, writer: Callable[[AtomicWriter], AtomicWriter] | None = None,
    judged: JudgedVersions | None = None, allowance: CaseAllowance | None = None,
) -> ServicesWorld:
    """``writer`` wraps the atomic writer of the store (a write that fails)."""
    return _world(dispatch_fs_world(tmp_path), fs_store(tmp_path, writer), evidence, links, delivery, judged, allowance)


def memory_world(
    tmp_path: Path, evidence: ServiceEvidence | None = None, links: Callable[[LinkNotes], LinkNotes] | None = None,
    delivery: Callable[[MessageDelivery], MessageDelivery] | None = None, judged: JudgedVersions | None = None,
    allowance: CaseAllowance | None = None,
) -> ServicesWorld:
    return _world(dispatch_memory_world(tmp_path), memory_store(tmp_path), evidence, links, delivery, judged, allowance)


def fs_rework(tmp_path: Path) -> ReworkContext:
    return fs_world(tmp_path).rework


def memory_rework(tmp_path: Path) -> ReworkContext:
    return memory_world(tmp_path).rework


def normalizer(tmp_path: Path) -> ContractNormalizer:
    return TextContractNormalizer()


def admitting_evidence(tmp_path: Path) -> ServiceEvidence:
    return AdmittingServiceEvidence()


def refusing_evidence(tmp_path: Path) -> ServiceEvidence:
    return RefusingServiceEvidence()


class NoJudgedVersions(JudgedVersions):
    """No delivery was judged and no relayed rework changed one: no rework needs a base (the default of the worlds)."""

    def base(self, owner: str, service: str, revises: str) -> JudgedBase | None:
        return None


class FixedJudgedVersions(JudgedVersions):
    """The bases a test puts in, by the task a rework revises; ``asked`` records every question as ``(owner, service, revises)``."""

    def __init__(self, bases: Mapping[str, JudgedBase] | None = None) -> None:
        self.bases = dict(bases or {})
        self.asked: list[tuple[str, str, str]] = []

    def base(self, owner: str, service: str, revises: str) -> JudgedBase | None:
        self.asked.append((owner, service, revises))
        return self.bases.get(revises)


class FixedAllowance(CaseAllowance):
    """What is left of the approved runs of a case, by the task a rework revises (``answers``; a missing key is None). ``error``, when set, is raised
    instead; ``asked`` records every question as ``(owner, service, revises)``."""

    def __init__(self, answers: Mapping[str, int | None] | None = None, error: Exception | None = None) -> None:
        self.answers = dict(answers or {})
        self.error = error
        self.asked: list[tuple[str, str, str]] = []

    def left(self, owner: str, service: str, revises: str) -> int | None:
        self.asked.append((owner, service, revises))
        if self.error is not None:
            raise self.error
        return self.answers.get(revises)


JUDGED_TASK = "20260101T000000000001-root-aaaa"  # the task ``fixed_judged_versions`` has a base for
ALLOWANCE_TASK = "20260101T000000000001-root-bbbb"  # the task ``fixed_case_allowance`` has an answer for


def no_judged_versions(tmp_path: Path) -> JudgedVersions:
    return NoJudgedVersions()


def fixed_judged_versions(tmp_path: Path) -> JudgedVersions:
    return FixedJudgedVersions({JUDGED_TASK: JudgedBase(
        task=JUDGED_TASK, result="20260101T000000000002-ceo-bbbb", commit="a" * 40, relayed=("20260101T000000000003-root-cccc",),
        changed=("ceo/memo.md", "ceo/other.md"), texts=(("ceo/memo.md", "the judged text"),),
    )})


def no_case_allowance(tmp_path: Path) -> CaseAllowance:
    return FixedAllowance({})


def fixed_case_allowance(tmp_path: Path) -> CaseAllowance:
    return FixedAllowance({ALLOWANCE_TASK: 7})


def hints_fs(tmp_path: Path) -> ServiceHints:
    return fs_world(tmp_path).hints


def hints_memory(tmp_path: Path) -> ServiceHints:
    return memory_world(tmp_path).hints


PURE = {"ContractNormalizer"}  # text in, text out: one implementation, no fake (the other contract suites run over disk and over memory)

IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    ServiceStore: [fs_store, memory_store],
    ServiceCatalog: [fs_world, memory_world],
    ServiceCommands: [fs_world, memory_world],
    ServiceHints: [hints_fs, hints_memory],
    ContractNormalizer: [normalizer],
    ReworkContext: [fs_rework, memory_rework],
    ServiceEvidence: [admitting_evidence, refusing_evidence],
    JudgedVersions: [no_judged_versions, fixed_judged_versions],
    CaseAllowance: [no_case_allowance, fixed_case_allowance],
}
