"""``FolderDeliverableChecks``: the files of a contract's deliverable folder (or the one file it names) that are not what the team delivered as checked
(design 6.3). Nothing here touches the disk or git: the folder is a ``DeliverableFolder``, the checked versions are ``CheckedVersions``.

The services whose contracts name one place form a *group*, shown as one block; whether a contract names a folder or a file is decided per contract
before the groups are formed (DR-45). The comparison basis of a group is the union of the results of all its services and of the actor's own one-off
tasks, because the default ``deliverables/`` folder is shared by everything root requests. Only the user's own verdict settles a finding."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath

from ..kernel import Clock, Message, artifact_paths, latest_results, msg_time
from ..mail import MailboxReader
from ..services import Contract, ServiceCatalog
from ._deliverables import READ_TOTAL
from ._ports import BlobIds, CheckedVersions, DeliverableFolder, FolderFile, Located
from .api import Case, CaseHistory, DeliverableChecks, DeliverableFinding, questions_open

GIT_PAIRS = 40  # (result, path) pairs one call may ask git about
GIT_SECONDS = 5.0  # seconds of one call after which no more pairs are asked of git
RESULTS_PER_SOURCE = 20  # the newest done results of each service (and of the actor's one-off tasks) that are candidates
PATHS_PER_RESULT = 10  # the first artifact paths of a result that are candidates
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _us(moment: datetime | None) -> int | None:
    """Microseconds since the epoch, the unit of a file's mtime; None for none."""
    return None if moment is None else (moment - EPOCH) // timedelta(microseconds=1)


def _in_the_organization(path: str) -> bool:
    """An artifact path that can be compared: relative to the organization, without a ``..``, ``.`` or empty segment (a directory listed with a trailing
    slash has one) and without a NUL byte (no file has one; an agent's result can list one)."""
    return bool(path) and "\0" not in path and not path.startswith("/") and all(part not in ("", ".", "..") for part in path.split("/"))


@dataclass(frozen=True)
class _Pair:
    """One path a done result listed: the team's artifact, with the task it answers and the case that task belongs to."""

    result: Message
    path: str
    task: Message
    case: Case | None


def _judged(pair: _Pair) -> bool:
    """Does the pair's delivery carry a human-tier verdict: the user's own, given on its task after its result (``deliveries_of``'s rule; counted or
    voided)? One given on an earlier blocked result is on no delivery."""
    return pair.case is not None and any(
        v.tier == "human" and v.task_id == pair.task.id and v.message.id > pair.result.id for v in pair.case.verdicts
    )


@dataclass
class _Group:
    place: Located
    state: str  # what is there: folder | file | link | unreadable (decided by the walk, before the groups are formed)
    contracts: list[Contract]  # the contracts that name this place
    files: dict[str, list[Contract]] = field(default_factory=dict)  # a folder group: the contracts that name a file inside it, by file name
    basis: _Basis | None = None  # made when the first file of the group needs it

    @property
    def members(self) -> list[Contract]:
        return [*self.contracts, *(c for named in self.files.values() for c in named)]

    @property
    def services(self) -> tuple[str, ...]:
        return tuple(sorted({c.name for c in self.members}))


@dataclass
class _Basis:
    pairs: list[_Pair]  # newest result first
    cases: list[Case]  # every case of every service of the group
    floor: int | None  # microseconds: files last written before the earliest contract of the group are the user's own older files


@dataclass
class _Call:
    """What one ``findings`` call keeps: the actor, what is left to read and to ask git, and the checked versions it already knows. The actor's mail is
    read when a comparison first needs it (``sent``, ``latest``)."""

    actor: str
    started: float
    settled: bool = False  # settled findings are returned, marked, instead of left out
    left: int = READ_TOTAL
    hexlen: int = 40  # the length of the ids of the repository's object format, once git has answered one
    asked: set[tuple[str, str]] = field(default_factory=set)
    known: dict[tuple[str, str], str | None] = field(default_factory=dict)
    from_git: set[tuple[str, str]] = field(default_factory=set)  # the (result id, path) keys of ``known`` that git answered, not the organization's file now
    current: dict[tuple[str, int], str | None] = field(default_factory=dict)
    sent: list[Message] | None = None
    latest: dict[str, Message] | None = None


class FolderDeliverableChecks(DeliverableChecks):
    def __init__(
        self, catalog: ServiceCatalog, history: CaseHistory, mail: MailboxReader, folders: DeliverableFolder, versions: CheckedVersions,
        blobs: BlobIds, clock: Clock,
    ) -> None:
        self._catalog = catalog
        self._history = history
        self._mail = mail
        self._folders = folders
        self._versions = versions
        self._blobs = blobs
        self._clock = clock

    def findings(self, actor: str, service: str | None = None, *, settled: bool = False) -> list[DeliverableFinding]:
        chosen = [g for g in self._groups(actor) if service is None or any(c.name == service for c in g.members)]
        if not chosen:
            return []
        call = _Call(actor, self._clock.monotonic(), settled)
        return [found for group in chosen for found in self._group(call, group)]

    # ---------------------------------------------------------------------------------------------------- groups

    def _groups(self, actor: str) -> list[_Group]:
        """The places the contracts of ``actor``'s services name, in order of their paths; a contract that names a file in a folder that is also a group
        joins that group (DR-45)."""
        placed: list[tuple[Contract, Located, str]] = []
        for contract in self._catalog.requestable_services(actor):
            place = self._folders.locate(contract.deliverable.get("path"))
            state = "missing" if place is None else self._folders.kind(place)
            if place is not None and state != "missing":
                placed.append((contract, place, state))
        groups: dict[str, _Group] = {}
        for contract, place, state in placed:
            if state != "file":
                key = str(place.named if place.link else place.target)
                groups.setdefault(key, _Group(place, state, [])).contracts.append(contract)
        for contract, place, state in placed:
            if state == "file":
                parent = groups.get(str(place.target.parent))
                if parent is not None and parent.state == "folder":
                    parent.files.setdefault(place.target.name, []).append(contract)
                else:
                    groups.setdefault(str(place.target), _Group(place, "file", [])).contracts.append(contract)
        return [groups[key] for key in sorted(groups)]

    def _group(self, call: _Call, group: _Group) -> list[DeliverableFinding]:
        read = self._folders.read(group.place, call.left)
        call.left -= read.used
        folder = read.folder or str(group.place.target)
        if read.state in ("link", "unreadable"):
            return [DeliverableFinding(folder, group.services, "", read.state, error=read.error)]
        if read.state != group.state:  # missing, or not what the walk saw a moment ago: nothing to say
            return []
        out: list[DeliverableFinding] = []
        listed = set()
        for entry in read.files:
            listed.add(entry.name)
            out += self._entry(call, group, folder, entry)
        for name in sorted(set(group.files) - listed):  # a file contract whose file is hidden or past the 200th entry: read on its own
            own = self._folders.read(Located(group.place.target / name, group.place.named / name), call.left)
            call.left -= own.used
            if own.state == "link":
                out.append(DeliverableFinding(folder, group.services, name, "link"))
            elif own.state == "file":
                out += self._entry(call, group, folder, own.files[0])
        return out

    # ---------------------------------------------------------------------------------------------------- one file

    def _entry(self, call: _Call, group: _Group, folder: str, entry: FolderFile) -> list[DeliverableFinding]:
        single = group.state == "file"  # a contract that names a file, outside any folder group
        if entry.kind != "file":  # a link, a file too large, past the budget, or one that could not be read: shown as it is
            return [DeliverableFinding(folder, group.services, entry.name, entry.kind, error=entry.error, file=single)]
        if group.basis is None:  # the results to compare with are looked up for the first file that is compared
            group.basis = self._basis(call, group)
        basis = group.basis
        if basis.floor is not None and entry.mtime_us < basis.floor:
            return []  # written before the earliest contract of the group: the user's own older file
        by_file_rule = single or entry.name in group.files
        kind, pair, ids = self._file_rule(call, basis, entry) if by_file_rule else self._folder_rule(call, basis, entry)
        if not kind:
            return []
        if pair is None or kind == "unknown":
            settled = self._settled(entry.mtime_us, basis.cases)  # a verdict on any case of the group
            if settled and not call.settled:
                return []
            return [DeliverableFinding(folder, group.services, entry.name, "unknown", file=single, written=entry.mtime_us, settled=settled)]
        settled = self._settled(entry.mtime_us, [pair.case] if pair.case is not None else [])
        if settled and not call.settled:
            return []
        if kind == "relayed":
            return [
                DeliverableFinding(
                    folder, group.services, entry.name, "relayed", task=pair.task.id, relayed=ids, file=single, written=entry.mtime_us, settled=settled,
                )
            ]
        withheld = questions_open(pair.task, pair.result, pair.case, call.sent or []) > 0
        return [
            DeliverableFinding(
                folder, group.services, entry.name, "differs", pair.path, pair.task.id, withheld, file=single, written=entry.mtime_us, settled=settled,
            )
        ]

    def _folder_rule(self, call: _Call, basis: _Basis, entry: FolderFile) -> tuple[str, _Pair | None, tuple[str, ...]]:
        """A file of a folder contract: compared with the checked version of the team's artifact of the same name, newest first; else with any
        version the team has. Past a newest version that root's relayed rework wrote, the file may equal the delivery the user saw: ``relayed``, with the
        delivery's pair and the ids of the relayed reworks after it, oldest first (design 7.2). When several deliveries of the case equal the file as git
        has it, the pair is the one the user judged (``_judged_tie``: of several, the newest result among them), else the newest as before (F-G0-1)."""
        newest: _Pair | None = None
        relayed: list[str] = []  # the relayed tasks of the pairs walked past, newest first
        named = [p for p in basis.pairs if PurePosixPath(p.path).name == entry.name]  # newest first
        for at, pair in enumerate(named):
            checked = self._checked(call, pair)
            if checked is None:  # a pair unknown on both sides (git and the organization) is dropped
                continue
            if self._same(entry, checked):
                if newest is None:
                    return "", None, ()
                return "relayed", self._judged_tie(call, entry, pair, named[at + 1 :]) or pair, tuple(reversed(relayed))
            newest = newest or pair
            if pair.task.source != "relayed":
                break  # a task that is not a relayed rework ends the walk
            relayed.append(pair.task.id)
        if newest is not None:
            return "differs", newest, ()
        if any(self._same(entry, now) for pair in basis.pairs if (now := self._now(call, pair.path)) is not None):
            return "", None, ()  # a renamed copy of something the organization holds now
        if any(self._same(entry, checked) for pair in basis.pairs if (checked := self._checked(call, pair)) is not None):
            return "", None, ()  # ... or of something the team checked
        return "unknown", None, ()

    def _judged_tie(self, call: _Call, entry: FolderFile, pair: _Pair, later: Sequence[_Pair]) -> _Pair | None:
        """The delivery the file equals that the user judged, when ``pair`` (the newest result that equals it) is one of several (F-G0-1, the manager's
        ruling): ``pair`` itself when it carries a human-tier verdict, else the first of the ``later`` (older) pairs of the same case that git gave an
        equal version for and that carries one. None when nothing was given by git, for a one-off task, or when no equal delivery was judged: the
        caller keeps ``pair``. A version from the organization's file now is no candidate: it is not what the team checked at that result (design 4.5)."""
        if pair.case is None or (pair.result.id, pair.path) not in call.from_git:
            return None
        if _judged(pair):
            return pair
        for other in later:
            if other.case is None or other.case.id != pair.case.id or not _judged(other):
                continue
            checked = self._checked(call, other)
            if checked is not None and (other.result.id, other.path) in call.from_git and self._same(entry, checked):
                return other
        return None

    def _file_rule(self, call: _Call, basis: _Basis, entry: FolderFile) -> tuple[str, _Pair | None, tuple[str, ...]]:
        """A file a contract names: compared with the team's artifacts of the same name, else with those of its newest result (a contract that names
        ``memo.md`` while the team writes ``2026-10-05-memo.md``). Never ``unknown`` while the group has a result to compare with (DR-45). A file equal
        to an artifact that only relayed reworks' artifacts are newer than is ``relayed``; with the user's own rework in between it is no finding."""
        if not basis.pairs:
            return "unknown", None, ()
        same_name = [p for p in basis.pairs if PurePosixPath(p.path).name == entry.name]
        pairs = same_name or [p for p in basis.pairs if p.result.id == basis.pairs[0].result.id]
        known, only_relayed = False, True
        relayed: list[str] = []  # the relayed tasks of the known pairs walked past, newest first
        for pair in pairs:
            checked = self._checked(call, pair)
            if checked is None:
                continue
            known = True
            if self._same(entry, checked):
                return ("relayed", pair, tuple(reversed(relayed))) if relayed and only_relayed else ("", None, ())
            if pair.task.source == "relayed":
                relayed.append(pair.task.id)
            else:
                only_relayed = False
        return ("differs", pairs[0], ()) if known else ("unknown", None, ())

    def _same(self, entry: FolderFile, blob: str) -> bool:
        return self._blobs.of(entry.data, len(blob)) == blob

    def _settled(self, mtime_us: int, cases: list[Case]) -> bool:
        """Has the user's own verdict (human tier) been recorded on one of these cases at or after the file was last written? A relayed one never
        settles anything: the assistant's own ``feedback`` right after its own edit leaves the finding."""
        return any(
            v.tier == "human" and (stamp := _us(msg_time(v.message))) is not None and stamp >= mtime_us for case in cases for v in case.verdicts
        )

    # ---------------------------------------------------------------------------------------------------- the basis

    def _basis(self, call: _Call, group: _Group) -> _Basis:
        if call.latest is None or call.sent is None:  # the actor's mail, read once per call
            call.sent, call.latest = list(self._mail.sent(call.actor)), latest_results(self._mail.received(call.actor))
        latest, sent = call.latest, call.sent
        cases: list[Case] = []
        done: dict[str, tuple[Message, Message, Case | None]] = {}  # result id -> (result, its task, the task's case)
        for contract in group.members:
            mine = self._history.cases(contract.owner, contract.name)
            cases += mine
            candidates = [
                (r, task, case) for case in mine for task in case.tasks if (r := latest.get(task.id)) is not None and r.status == "done"
            ]
            for r, task, case in sorted(candidates, key=lambda item: item[0].id, reverse=True)[:RESULTS_PER_SOURCE]:
                done[r.id] = (r, task, case)
        one_off = [
            (r, task, None) for task in sent
            if task.type == "task" and not task.service and (r := latest.get(task.id)) is not None and r.status == "done"
        ]
        for r, task, _ in sorted(one_off, key=lambda item: item[0].id, reverse=True)[:RESULTS_PER_SOURCE]:
            done[r.id] = (r, task, None)
        pairs: list[_Pair] = []
        for r, task, owner in sorted(done.values(), key=lambda item: item[0].id, reverse=True):
            paths = [p for p in artifact_paths(r.body) if _in_the_organization(p)]
            pairs += [_Pair(r, path, task, owner) for path in dict.fromkeys(paths[:PATHS_PER_RESULT])]
        created = [stamp for c in group.members if (stamp := _us(c.created)) is not None]
        return _Basis(pairs, cases, min(created) if created else None)

    def _checked(self, call: _Call, pair: _Pair) -> str | None:
        """The blob id of the team's version of ``pair``: git's, while the bound of 40 pairs and 5 seconds allows, else the organization's file now."""
        key = (pair.result.id, pair.path)
        if key not in call.known:
            blob = None
            if len(call.asked) < GIT_PAIRS and self._clock.monotonic() - call.started < GIT_SECONDS:
                call.asked.add(key)
                at = self._versions.at_result(pair.result, pair.path)
                if at is not None:
                    blob = at[1]
                    call.from_git.add(key)
                    call.hexlen = len(blob)
            call.known[key] = blob if blob is not None else self._now(call, pair.path)
        return call.known[key]

    def _now(self, call: _Call, path: str) -> str | None:
        """The blob id of the organization's file ``path`` now (no git), asked once per call and path."""
        key = (path, call.hexlen)
        if key not in call.current:
            call.current[key] = self._versions.current(path, call.hexlen)
        return call.current[key]
