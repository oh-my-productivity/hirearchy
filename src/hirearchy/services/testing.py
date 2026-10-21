"""The services over files on disk and over files in memory, the fake store, and the registry the contract suites iterate over.

``MemoryServiceStore`` is the in-memory ``ServiceStore``: it keeps the text of every file under the path the real store would use, so that it round
trips through the same frontmatter and answers like the real one. ``ServicesWorld`` is what a test gets: the ports of the package built over one
organization (the agents, mailboxes, message sender, settings and clock of ``dispatch``'s world), the events they emitted, and the means to look at
the files.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from ..dispatch import ReworkContext
from ..dispatch.testing import MEMORY_ROOT, DispatchWorld, PostedDelivery
from ..dispatch.testing import fs_world as dispatch_fs_world
from ..dispatch.testing import memory_world as dispatch_memory_world
from ..kernel import ROOT, JsonObject, OrgError, OrgPaths, join_frontmatter, norm, split_frontmatter
from ..kernel.testing import ListEventSink, fs_atomic_writer
from ._amend import ContractAmender
from ._catalog import ContractServiceCatalog
from ._commands import RuleServiceCommands
from ._define import RuleContractDefiner
from ._feedback import RuleClientFeedback
from ._hints import ServiceReportHints
from ._normalizer import TextContractNormalizer
from ._parse import as_int, merged_versions
from ._places import OrgServicePlaces
from ._playbook import RulePlaybookReviser
from ._protocols import ServicePlaces
from ._request import RuleServiceRequester, TextRequestBodies
from ._retire import RuleServiceRetirement
from ._rework import ServiceReworkContext
from ._store import FsServiceStore
from ._texts import CappedPlaybookTexts, DirectReportOwners, EventedPlaybookWriter
from .api import (
    Admission,
    ContractNormalizer,
    ServiceCatalog,
    ServiceCommands,
    ServiceEvidence,
    ServiceHints,
    ServiceStore,
    normalize_evidence,
    normalize_links,
)

# ------------------------------------------------------------------------------ the fake store


class MemoryServiceStore(ServiceStore):
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


# ------------------------------------------------------------------------------ the stand-ins for the evidence gate


class AdmittingServiceEvidence(ServiceEvidence):
    """The gate that lets everything through: admits every revision by rule ``b`` and accepts every link (the ids normalized). The default of the
    worlds: the tests of the commands that call the gate do not need its judgement, ``reflection`` has the real one."""

    def links(self, owner: str, service: str, ids: Sequence[str], *, verdict: str | None = None) -> tuple[str, ...]:
        return normalize_links(list(ids))

    def admit(self, owner: str, service: str, evidence: Sequence[str], reason: str, *, exempt: str | None = None) -> Admission:
        ids = normalize_evidence(list(evidence))
        return Admission(exempt, ids, "no evidence needed") if exempt else Admission("b", ids, "admitted by the stand-in for the gate")


class RefusingServiceEvidence(AdmittingServiceEvidence):
    """The gate that refuses every revision that is not exempt, with the text it was given (the links as the admitting one)."""

    def __init__(self, text: str = "refused by the stand-in for the gate") -> None:
        self._text = text

    def admit(self, owner: str, service: str, evidence: Sequence[str], reason: str, *, exempt: str | None = None) -> Admission:
        if exempt:
            return super().admit(owner, service, evidence, reason, exempt=exempt)
        raise OrgError(self._text)


# ------------------------------------------------------------------------------ the worlds


@dataclass(frozen=True)
class StoreHarness:
    """A store and the means to look at its files."""

    store: ServiceStore
    places: ServicePlaces
    text: Callable[[str], str | None]  # the text of a file (path relative to the organization), None when there is none
    rels: Callable[[], list[str]]  # every file of the services, relative to the organization, sorted


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


def _text_on_disk(root: Path) -> Callable[[str], str | None]:
    def text(rel: str) -> str | None:
        path = root / rel
        return path.read_text(encoding="utf-8") if path.is_file() else None

    return text


def _rels_on_disk(root: Path) -> Callable[[], list[str]]:
    def rels() -> list[str]:
        return sorted(str(p.relative_to(root)) for p in root.glob("**/services/**/*.md"))

    return rels


def fs_store(tmp_path: Path) -> StoreHarness:
    places = OrgServicePlaces(OrgPaths(tmp_path))
    return StoreHarness(FsServiceStore(places, fs_atomic_writer(tmp_path).writer), places, _text_on_disk(tmp_path), _rels_on_disk(tmp_path))


def memory_store(tmp_path: Path) -> StoreHarness:
    places = OrgServicePlaces(OrgPaths(MEMORY_ROOT))
    store = MemoryServiceStore(places)

    def text(rel: str) -> str | None:
        return store.files.get(MEMORY_ROOT / rel)

    def rels() -> list[str]:
        return sorted(str(p.relative_to(MEMORY_ROOT)) for p in store.files)

    return StoreHarness(store, places, text, rels)


def _world(d: DispatchWorld, harness: StoreHarness, evidence: ServiceEvidence | None = None) -> ServicesWorld:
    places, store = harness.places, harness.store
    gate = evidence or AdmittingServiceEvidence()
    events, delivery = ListEventSink(), PostedDelivery(d.post)
    normalizer = TextContractNormalizer()
    catalog = ContractServiceCatalog(store, d.agents, places)
    owners, texts = DirectReportOwners(d.agents), CappedPlaybookTexts(d.settings)
    playbooks = EventedPlaybookWriter(store, d.clock, events)
    commands = RuleServiceCommands(
        RuleContractDefiner(d.agents, catalog, store, places, normalizer, ContractAmender(), texts, owners, playbooks, delivery, d.clock, events),
        RuleServiceRetirement(d.agents, catalog, store, owners, delivery, d.clock, events),
        RulePlaybookReviser(d.agents, catalog, texts, playbooks, delivery, gate),
        RuleServiceRequester(d.agents, catalog, d.mail, TextRequestBodies(), d.sender),
        RuleClientFeedback(d.agents, d.mail, d.sender, gate),
    )
    return ServicesWorld(
        commands=commands, catalog=catalog, store=store, hints=ServiceReportHints(catalog), evidence=gate,
        normalizer=normalizer,
        rework=ServiceReworkContext(d.mail, d.agents, catalog), places=places, d=d, events=events, text=harness.text, rels=harness.rels,
    )


def fs_world(tmp_path: Path, evidence: ServiceEvidence | None = None) -> ServicesWorld:
    return _world(dispatch_fs_world(tmp_path), fs_store(tmp_path), evidence)


def memory_world(tmp_path: Path, evidence: ServiceEvidence | None = None) -> ServicesWorld:
    return _world(dispatch_memory_world(tmp_path), memory_store(tmp_path), evidence)


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
}
